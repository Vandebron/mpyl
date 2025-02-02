"""
Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from git import Git, Repo
from git.objects import Commit
from gitdb.exc import BadName

from ...project import Project


@dataclass(frozen=True)
class Changeset:
    sha: str
    """Git hash for this revision"""
    _files_touched: dict[str, str]

    def files_touched(self, status: Optional[set[str]] = None):
        if not status or len(status) == 0:
            return set(self._files_touched.keys())

        return {file for file, s in self._files_touched.items() if s in status}

    @staticmethod
    def from_diff(sha: str, diff: set[str]):
        changes = {}
        for line in diff:
            parts = line.split("\t")
            if len(parts) == 2:
                changes[parts[1]] = parts[0]
            elif len(parts) == 3 and parts[0].startswith("R"):
                changes[parts[2]] = "R"
            else:
                logging.warning(f"Skipping unparseable diff output line {line}")

        return Changeset(sha, changes)

    @staticmethod
    def with_untracked_files(sha: str, diff: set[str], untracked_files: set[str]):
        changes = {}
        for line in diff:
            parts = line.split("\t")
            changes[parts[1]] = parts[0]

        for file in untracked_files:
            changes[file] = "U"

        return Changeset(sha, changes)

    @staticmethod
    def empty(sha: str):
        return Changeset(sha=sha, _files_touched={})

    def merge(self, other: "Changeset"):
        return Changeset(
            sha=self.sha,
            _files_touched={
                **self._files_touched,
                **other._files_touched,  # pylint: disable=protected-access
            },
        )


@dataclass(frozen=True)
class RepoCredentials:
    name: str
    url: str
    ssh_url: str
    user_name: str
    email: str
    password: str

    @property
    def to_url_with_credentials(self):
        parsed = urlparse(self.url)

        repo = f"{parsed.netloc}{parsed.path}"
        if not self.user_name:
            return f"{parsed.scheme}://{repo}"

        return f"{parsed.scheme}://{self.user_name or ''}{f':{self.password}' if self.password else ''}@{repo}"

    @staticmethod
    def from_config(config: dict):
        url = config["url"]
        ssh_url = f"{url.replace('https://', 'git@').replace('.com/', '.com:')}"
        return RepoCredentials(
            name=url.removeprefix("https://github.com/").removesuffix(".git"),
            url=url,
            ssh_url=ssh_url,
            user_name=config["userName"],
            email=config["email"],
            password=config["password"],
        )


@dataclass(frozen=True)
class RepoConfig:
    main_branch: str
    ignore_patterns: list[str]
    project_sub_folder: str
    project_file_name: str
    repo_credentials: Optional[RepoCredentials]

    @staticmethod
    def from_config(config: dict):
        git_config = config["vcs"]["git"]
        return RepoConfig.from_git_config(git_config=git_config)

    @staticmethod
    def from_git_config(git_config: dict):
        maybe_remote_config = git_config.get("remote", {})
        return RepoConfig(
            main_branch=git_config["mainBranch"],
            ignore_patterns=git_config.get("ignorePatterns", []),
            project_sub_folder=git_config.get("projectSubFolder", "deployment"),
            project_file_name=git_config.get("projectFile", "project.yml"),
            repo_credentials=(
                RepoCredentials.from_config(maybe_remote_config)
                if maybe_remote_config
                else None
            ),
        )


class Repository:  # pylint: disable=too-many-public-methods
    def __init__(self, config: RepoConfig, repo: Union[Repo, None] = None):
        self.config = config
        self._repo = repo or Repo(path=Git().rev_parse("--show-toplevel"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._repo.close()
        if exc_val:
            raise exc_val
        return self

    @staticmethod
    def from_clone(config: RepoConfig, repo_path: Path):
        creds = config.repo_credentials
        if not creds:
            raise ValueError("Cannot clone repository without credentials")

        if user_name := creds.user_name is None:
            return Repository(
                config=config,
                repo=Repo.clone_from(url=creds.ssh_url, to_path=repo_path),
            )

        repo = Repo.clone_from(
            url=creds.to_url_with_credentials,
            to_path=repo_path,
        )
        with repo.config_writer() as writer:
            writer.set_value("user", "name", user_name)
            writer.set_value("user", "email", creds.email or "somebody@somewhere.com")

        return Repository(config=config, repo=repo)

    @property
    def get_sha(self):
        return self._repo.head.commit.hexsha

    @property
    def get_branch(self) -> Optional[str]:
        if self._repo.head.is_detached:
            return None
        return self._repo.active_branch.name

    def _safe_ref_parse(self, branch: str) -> Union[Commit, None]:
        try:
            return self._repo.rev_parse(branch)
        except BadName as exc:
            logging.debug(f"Does not exist: {exc}")
            return None

    @property
    def root_commit_hex(self) -> str:
        return self._repo.git.rev_list("--max-parents=0", "HEAD").splitlines()[-1]

    @property
    def base_revision(self) -> Union[Commit, None]:
        return self._safe_ref_parse(self.main_branch)

    @property
    def remote_url(self) -> Optional[str]:
        if self._repo.remotes:
            return self._repo.remote().url
        return None

    @property
    def root_dir(self) -> Path:
        return Path(self._repo.git_dir).parent

    @property
    def main_branch(self) -> str:
        return self.config.main_branch

    def __get_filter_patterns(self):
        return ["--"] + [f":!{pattern}" for pattern in self.config.ignore_patterns]

    def changes_in_branch(self) -> Changeset:
        return Changeset.from_diff(self.get_sha, self.changed_files_in_branch())

    def changed_files_in_branch(self) -> set[str]:
        # TODO pass the base_branch as a build parameter, not all branches  # pylint: disable=fixme
        #  are created from the main branch
        #  Also throw a more specific exception if the base branch is not found
        base_branch = self.main_branch
        diff = set(
            self._repo.git.diff(f"{base_branch}...HEAD", name_status=True).splitlines()
        )
        return diff

    def changes_in_branch_including_local(self) -> Changeset:
        local_changes = set(
            self._repo.git.diff(
                self.__get_filter_patterns(), None, name_status=True
            ).splitlines()
        )
        return Changeset.with_untracked_files(
            sha=self.get_sha,
            diff=self.changed_files_in_branch() | local_changes,
            untracked_files=set(self._repo.untracked_files),
        )

    def changes_in_tagged_commit(self, logger: logging.Logger, tag: str) -> Changeset:
        head_commit = self._repo.head.commit
        tag_commit = self._repo.tag(f"refs/tags/{tag}").commit
        logger.debug(f"HEAD revision: {head_commit}, tag revision: {tag_commit}")

        if head_commit != tag_commit:
            logger.error(
                f"HEAD is at {head_commit} not at expected {tag_commit} for tag `{tag}`"
            )
            return Changeset.empty(self.get_sha)

        diff = set(self._repo.git.diff(f"{tag}^..{tag}", name_status=True).splitlines())
        return Changeset.from_diff(sha=tag_commit.hexsha, diff=diff)

    def changes_from_file(
        self, logger: logging.Logger, changed_files_path: str
    ) -> Changeset:
        with open(changed_files_path, encoding="utf-8") as file:
            logger.debug(
                f"Creating Changeset based on changed files in {changed_files_path}"
            )
            changed_files = json.load(file)
            return Changeset(sha=self.get_sha, _files_touched=changed_files)

    def create_branch(self, branch_name: str):
        return self._repo.git.checkout("-b", f"{branch_name}")

    @property
    def has_changes(self) -> bool:
        return self._repo.is_dirty(untracked_files=True)

    def stage(self, path: str):
        return self._repo.git.add(path)

    def commit(self, message: str):
        return self._repo.git.commit("-m", message)

    def pull(self):
        return self._repo.git.pull()

    def add_note(self, note: str):
        return self._repo.git.notes("add", "-m", note)

    def push(self, branch: str):
        return self._repo.git.push("--set-upstream", "origin", branch)

    def checkout_branch(self, branch_name: str):
        self._repo.git.switch(branch_name)

    def remote_branch_exists(self, branch_name: str) -> bool:
        return self._repo.git.ls_remote("origin", branch_name) != ""

    def find_projects(self, folder_pattern: str = "") -> list[str]:
        """
        returns a set of all project.yml files
        :param folder_pattern: project paths are filtered on this pattern
        :param project_file_name: if project files are named differently than `project.yml`
        """
        folder = f"*{folder_pattern}*/{self.config.project_sub_folder}"
        projects_pattern = f"{folder}/{self.config.project_file_name}"
        overrides_pattern = Project.to_override_pattern(projects_pattern)

        def files(pattern: str):
            return set(
                self._repo.git.ls_files(pattern, recurse_submodules=True).splitlines()
            )

        def deleted(pattern: str):
            return set(self._repo.git.ls_files("-d", pattern).splitlines())

        projects = files(projects_pattern) | files(overrides_pattern)
        deleted = deleted(projects_pattern) | deleted(overrides_pattern)

        return sorted(projects - deleted)
