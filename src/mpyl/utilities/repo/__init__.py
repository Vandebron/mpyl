""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from git import Git, Repo, Remote
from git.objects import Commit
from gitdb.exc import BadName

from ...project import Project
from ...utilities.pyaml_env import parse_config


@dataclass(frozen=True)
class Changeset:
    sha: str
    """Git hash for this revision"""
    files_touched: set[str]
    """Paths to files that were altered in this hash"""
    BREAK_WORD = "hash "

    @staticmethod
    def empty(sha: str):
        return Changeset(sha=sha, files_touched=set())


@dataclass(frozen=True)
class RepoCredentials:
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
    repo_credentials: Optional[RepoCredentials]

    @staticmethod
    def from_config(config: dict):
        git_config = config["vcs"]["git"]
        return RepoConfig.from_git_config(git_config=git_config)

    @staticmethod
    def from_git_config(git_config: dict):
        maybe_remote_config = git_config.get("remote", None)
        return RepoConfig(
            main_branch=git_config["mainBranch"],
            ignore_patterns=git_config.get("ignorePatterns", []),
            repo_credentials=RepoCredentials.from_config(maybe_remote_config)
            if maybe_remote_config
            else None,
        )


class Repository:  # pylint: disable=too-many-public-methods
    def __init__(self, config: RepoConfig, repo_path: Optional[Path] = None):
        self._config = config
        self._root_dir = repo_path or Git().rev_parse("--show-toplevel")
        self._repo = Repo(
            path=self._root_dir
        )  # pylint: disable=attribute-defined-outside-init

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

        repo = Repo.clone_from(
            url=creds.to_url_with_credentials,
            to_path=repo_path,
        )
        user_name = creds.user_name
        with repo.config_writer() as writer:
            writer.set_value("user", "name", user_name)
            writer.set_value("user", "email", creds.email or "somebody@somwhere.com")

        return Repository(config=config, repo_path=repo_path)

    @property
    def get_sha(self):
        return self._repo.head.commit.hexsha

    @property
    def get_branch(self) -> Optional[str]:
        if self._repo.head.is_detached:
            return None
        return self._repo.active_branch.name

    def _safe_ref_parse(self, branch: str) -> Optional[Commit]:
        try:
            return self._repo.rev_parse(branch)
        except BadName as exc:
            logging.debug(f"Does not exist: {exc}")
            return None

    @property
    def root_commit_hex(self) -> str:
        return self._repo.git.rev_list("--max-parents=0", "HEAD").splitlines()[-1]

    @property
    def base_revision(self) -> Optional[Commit]:
        main = self.main_origin_branch
        return self._safe_ref_parse(main)

    @property
    def get_tag(self) -> Optional[str]:
        current_revision = self._repo.head.commit
        current_tag = self._repo.git.tag(current_revision, points_at=True)
        logging.debug(f"Current revision: {current_revision} tag: {current_tag}")
        return current_tag

    @property
    def remote_url(self) -> Optional[str]:
        if self._repo.remotes:
            return self._repo.remote().url
        return None

    @property
    def root_dir(self) -> Path:
        return Path(self._root_dir)

    @property
    def main_branch(self) -> str:
        return self._config.main_branch.split("/")[-1]

    @property
    def main_origin_branch(self) -> str:
        parts = self._config.main_branch.split("/")
        if len(parts) > 1:
            return "/".join(parts)
        return f"origin/{self.main_branch}"

    def fit_for_tag_build(self, tag: str) -> bool:
        return len(self.changes_in_tagged_commit(tag).files_touched) > 0

    def __get_filter_patterns(self):
        return ["--"] + [f":!{pattern}" for pattern in self._config.ignore_patterns]

    def changes_in_branch(self) -> Changeset:
        return Changeset(self.get_sha, self.changed_files_in_branch())

    def changed_files_in_branch(self) -> set[str]:
        base = self._repo.merge_base(self.main_origin_branch, "HEAD")[0]
        if base:
            changed_files = self._repo.git.diff(
                f"HEAD..{base.hexsha}", name_only=True
            ).splitlines()
            return set(changed_files)

        raise ValueError(
            f"Cannot find merge base between {self.main_origin_branch} and the current branch"
        )

    def unversioned_files(self) -> set[str]:
        changed: set[str] = set(
            self._repo.git.diff(
                self.__get_filter_patterns(), None, name_only=True
            ).splitlines()
        )
        return changed.union(self._repo.untracked_files)

    def changes_in_branch_including_unversioned_files(self) -> Changeset:
        return Changeset(
            sha=self.get_sha,
            files_touched=(self.changed_files_in_branch() | self.unversioned_files()),
        )

    def changes_in_tagged_commit(self, current_tag: str) -> Changeset:
        curr_rev_tag = self.get_tag

        if curr_rev_tag != current_tag:
            logging.error(f"HEAD is at {curr_rev_tag} not at expected `{current_tag}`")
            return Changeset.empty(self.get_sha)

        parent_revs = self._repo.head.commit.parents
        if not parent_revs:
            logging.error(
                "HEAD is not at merge commit, cannot determine changed files."
            )
            return Changeset.empty(self.get_sha)
        logging.debug(f"Parent revisions: {parent_revs}")
        files_changed = self._repo.git.diff(
            f"{str(self._repo.head.commit)}..{str(parent_revs[0])}", name_only=True
        ).splitlines()
        return Changeset(sha=str(self.get_sha), files_touched=files_changed)

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

    def push(self, branch: str):
        return self._repo.git.push("--set-upstream", "origin", branch)

    def checkout_branch(self, branch_name: str):
        self._repo.git.switch(branch_name)

    def remote_branch_exists(self, branch_name: str) -> bool:
        return self._repo.git.ls_remote("origin", branch_name) != ""

    def find_projects(self, folder_pattern: str = "") -> list[str]:
        """returns a set of all project.yml files
        :type folder_pattern: project paths are filtered on this pattern
        """
        projects = set(
            self._repo.git.ls_files(
                f"*{folder_pattern}*/{Project.project_yaml_path()}"
            ).splitlines()
        ) | set(
            self._repo.git.ls_files(
                f"*{folder_pattern}*/{Project.project_overrides_yml_pattern()}"
            ).splitlines()
        )
        return sorted(projects)
