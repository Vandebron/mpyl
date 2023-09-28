""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""
import itertools
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
class Revision:
    ord: int
    """Ordinal number indicating how this revision ranks historically"""
    hash: str
    """Git hash for this revision"""
    files_touched: set[str]
    """Paths to files that were altered in this hash"""
    BREAK_WORD = "hash "

    @staticmethod
    def from_git_output(git_log_output: str, git_diff_output: str):
        """
        :param git_diff_output: output of `git log --pretty=format:"hash %H" --name-only
        --no-abbrev-commit <from>..<until>`
        :param git_log_output: output of `git diff --name-only <from>..<until>`
        """

        change_set = set(git_diff_output.splitlines())

        sections = []
        current_section: list[str] = []
        lines = git_log_output.splitlines()
        for line in lines:
            if line.startswith(Revision.BREAK_WORD):
                if current_section:
                    sections.append(current_section)
                current_section = [line.replace(Revision.BREAK_WORD, "")]
            else:
                current_section.append(line)

        if current_section:
            sections.append(current_section)

        revisions = [
            Revision(
                index,
                section[0],
                {line for line in section[1:] if line in change_set},
            )
            for index, section in enumerate(reversed(sections))
        ]
        return revisions


@dataclass(frozen=True)
class RepoCredentials:
    url: str
    user_name: str
    password: str

    @property
    def to_url(self):
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    @staticmethod
    def from_config(config: dict):
        return RepoCredentials(
            url=config["url"], user_name=config["userName"], password=config["password"]
        )


@dataclass(frozen=True)
class RepoConfig:
    main_branch: str
    ignore_patterns: list[str]
    repo_credentials: Optional[RepoCredentials]

    @staticmethod
    def from_config(config: dict):
        git_config = config["cvs"]["git"]
        maybe_remote_config = git_config.get("remote", None)
        return RepoConfig(
            main_branch=git_config["mainBranch"],
            ignore_patterns=git_config.get("ignorePatterns", []),
            repo_credentials=RepoCredentials.from_config(maybe_remote_config)
            if maybe_remote_config
            else None,
        )


class Repository:  # pylint: disable=too-many-public-methods
    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = Git().rev_parse("--show-toplevel")
        self._repo = Repo(
            self._root_dir
        )  # pylint: disable=attribute-defined-outside-init

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._repo.close()
        if exc_val:
            raise exc_val
        return self

    @property
    def has_valid_head(self):
        return self._repo.head.is_valid()

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
        return len(self.changes_in_tagged_commit(tag)) > 0

    def __get_filter_patterns(self):
        return ["--"] + [f":!{pattern}" for pattern in self._config.ignore_patterns]

    def changes_between(self, base_revision: str, head_revision: str) -> list[Revision]:
        command = [
            f'--pretty=format:"{Revision.BREAK_WORD}%H"',
            "--name-only",
            "--no-abbrev-commit",
            f"{base_revision}..{head_revision}",
            self.__get_filter_patterns(),
        ]

        revs = self._repo.git.log(*command).replace('"', "")
        changed_files = self._repo.git.diff(
            f"{base_revision}..{head_revision}", name_only=True
        )
        return Revision.from_git_output(revs, changed_files)

    def changes_in_branch(self) -> list[Revision]:
        base_ref = self.base_revision
        base_hex = base_ref.hexsha if base_ref else self.root_commit_hex

        head_hex = self._repo.active_branch.commit.hexsha

        return self.changes_between(base_hex, head_hex)

    def changes_in_commit(self) -> set[str]:
        changed: set[str] = set(
            self._repo.git.diff(
                self.__get_filter_patterns(), None, name_only=True
            ).splitlines()
        )
        return changed.union(self._repo.untracked_files)

    def changes_in_branch_including_local(self) -> list[Revision]:
        in_branch = self.changes_in_branch()
        in_branch.append(
            Revision(len(in_branch), self.get_sha, self.changes_in_commit())
        )
        return in_branch

    def changes_in_tagged_commit(self, current_tag: str) -> list[Revision]:
        curr_rev_tag = self.get_tag

        if curr_rev_tag != current_tag:
            logging.error(f"HEAD is at {curr_rev_tag} not at expected `{current_tag}`")
            return []

        return self.changes_in_merge_commit()

    def changes_in_merge_commit(self):
        parent_revs = self._repo.head.commit.parents
        if not parent_revs:
            logging.error(
                "HEAD is not at merge commit, cannot determine changed files."
            )
            return []
        logging.debug(f"Parent revisions: {parent_revs}")
        files_changed = self._repo.git.diff(
            f"{str(self._repo.head.commit)}..{str(parent_revs[0])}", name_only=True
        ).splitlines()
        return [Revision(ord=0, hash=str(self.get_sha), files_touched=files_changed)]

    def init_remote(self, url: Optional[str]) -> Remote:
        if url:
            return self._repo.create_remote("origin", url=url)

        return self._repo.remote()

    def fetch_main_branch(self):
        return self._repo.remote().fetch(
            f"{self.main_branch}:refs/remotes/{self.main_origin_branch}"
        )

    def fetch_pr(self, pr_number: int):
        return self._repo.remote().fetch(f"pull/{pr_number}/head:PR-{pr_number}")

    @staticmethod
    def clone_from_branch(
        branch_name: str, url: str, base_branch: str, config_path: Path, path: Path
    ):
        Repo.clone_from(
            url,
            path,
            allow_unsafe_protocols=True,
            shallow_exclude=base_branch,
            single_branch=True,
            branch=branch_name,
        )
        parsed_config = parse_config(config_path)
        return Repository(RepoConfig.from_config(parsed_config))

    def checkout_branch(self, branch_name: str):
        self._repo.git.switch(branch_name)

    def does_local_branch_exist(self, branch_name: str) -> bool:
        local_branches = [
            branch.strip(" ") for branch in self._repo.git.branch("--list").splitlines()
        ]
        logging.debug(f"Found local branches: {local_branches}")
        return branch_name in local_branches

    def delete_branch(self, branch_name: str):
        self._repo.git.branch("-D", branch_name)

    def find_projects(self, folder_pattern: str = "") -> list[str]:
        """returns a set of all project.yml files
        :type folder_pattern: project paths are filtered on this pattern
        """
        projects = set(
            self._repo.git.ls_files(
                f"*{folder_pattern}*/{Project.project_yaml_path()}"
            ).splitlines()
        )
        return sorted(projects)
