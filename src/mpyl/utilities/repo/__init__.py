""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from git import Git, Repo, Remote

from ...project import Project


@dataclass(frozen=True)
class Revision:
    ord: int
    """Ordinal number indicating how this revision ranks historically"""
    hash: str
    """Git hash for this revision"""
    files_touched: set[str]
    """Paths to files that were altered in this hash"""


@dataclass(frozen=True)
class RepoCredentials:
    url: str
    user_name: str
    password: str

    @property
    def to_url_with_credentials(self):
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{self.user_name}:{self.password}@{parsed.netloc}{parsed.path}"

    @staticmethod
    def from_config(config: Dict):
        return RepoCredentials(
            url=config["url"], user_name=config["userName"], password=config["password"]
        )


@dataclass(frozen=True)
class RepoConfig:
    main_branch: str
    ignore_patterns: list[str]
    repo_credentials: Optional[RepoCredentials]

    @staticmethod
    def from_config(config: Dict):
        git_config = config["cvs"]["git"]
        maybe_remote_config = git_config.get("remote", None)
        return RepoConfig(
            main_branch=git_config["mainBranch"],
            ignore_patterns=git_config.get("ignorePatterns", []),
            repo_credentials=RepoCredentials.from_config(maybe_remote_config)
            if maybe_remote_config
            else None,
        )


class Repository:
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
        return self

    @property
    def get_sha(self):
        return self._repo.head.commit.hexsha

    @property
    def get_short_sha(self):
        return self._repo.git.rev_parse(self._repo.head, short=True)

    @property
    def get_branch(self) -> Optional[str]:
        if self._repo.head.is_detached:
            return None
        return self._repo.active_branch.name

    @property
    def get_tag(self) -> Optional[str]:
        current_revision = self._repo.head.commit
        current_tag = self._repo.git.describe(current_revision, tags=True)
        logging.debug(f"Current revision: {current_revision} tag: {current_tag}")
        return current_tag

    @property
    def get_remote_url(self):
        return self._repo.remote().url

    def root_dir(self) -> Path:
        return Path(self._root_dir)

    @property
    def main_branch(self) -> str:
        return self._config.main_branch

    def __get_filter_patterns(self):
        return ["--"] + [f":!{pattern}" for pattern in self._config.ignore_patterns]

    @property
    def latest_tag(self) -> str:
        return str(
            sorted(self._repo.tags, key=lambda t: t.commit.committed_datetime)[-1]
        )

    def changes_in_branch(self) -> list[Revision]:
        revisions = reversed(
            list(self._repo.iter_commits(f"{self._config.main_branch}..HEAD"))
        )
        return [
            Revision(
                count,
                str(rev),
                self._repo.git.diff_tree(
                    self.__get_filter_patterns(),
                    no_commit_id=True,
                    name_only=True,
                    r=str(rev),
                ).splitlines(),
            )
            for count, rev in enumerate(revisions)
        ]

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
            logging.error(
                f"HEAD is not at {curr_rev_tag} not at expected {current_tag}"
            )
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
            f"{str(parent_revs[0])}..{str(parent_revs[1])}", name_only=True
        ).splitlines()
        return [Revision(ord=0, hash=str(self.get_sha), files_touched=files_changed)]

    @property
    def main_branch_pulled(self) -> bool:
        branch_names = list(map(lambda n: n.name, self._repo.references))
        return f"{self._config.main_branch}" in branch_names

    def __get_remote(self) -> Remote:
        default_remote = self._repo.remote("origin")
        if "https:" not in default_remote.url or self._config.repo_credentials is None:
            return default_remote

        return default_remote.set_url(
            self._config.repo_credentials.to_url_with_credentials
        )

    def pull_main_branch(self):
        remote = self.__get_remote()
        main = self._config.main_branch
        return remote.fetch(f"+refs/heads/{main}:refs/heads/{main}")

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
