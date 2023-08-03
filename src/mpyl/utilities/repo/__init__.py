""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""
import itertools
import logging

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from git import Git, Repo, Remote
from git.objects import Commit
from gitdb.exc import BadName

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
    def get_short_sha(self):
        return self._repo.git.rev_parse(self._repo.head, short=True)

    @property
    def get_branch(self) -> Optional[str]:
        if self._repo.head.is_detached:
            return None
        return self._repo.active_branch.name

    @property
    def base_revision(self) -> Optional[Commit]:
        try:
            return self._repo.rev_parse(self.main_origin_branch)
        except BadName as exc:
            logging.debug(f"Does not exist: {exc}")
            return None

    @property
    def get_tag(self) -> Optional[str]:
        current_revision = self._repo.head.commit
        current_tag = self._repo.git.describe(current_revision, tags=True)
        logging.debug(f"Current revision: {current_revision} tag: {current_tag}")
        return current_tag

    @property
    def remote_url(self) -> Optional[str]:
        if self._repo.remotes:
            return self._repo.remote().url
        return None

    def root_dir(self) -> Path:
        return Path(self._root_dir)

    @property
    def main_branch(self) -> str:
        return self._config.main_branch.replace("origin/", "")

    @property
    def main_origin_branch(self) -> str:
        return f"origin/{self.main_branch}"

    def __get_filter_patterns(self):
        return ["--"] + [f":!{pattern}" for pattern in self._config.ignore_patterns]

    @property
    def latest_tag(self) -> str:
        return str(
            sorted(self._repo.tags, key=lambda t: t.commit.committed_datetime)[-1]
        )

    def __to_revision(
        self, count: int, revision: Commit, files_touched_in_branch: set[str]
    ) -> Revision:
        files_in_revision = set(
            self._repo.git.diff_tree(
                self.__get_filter_patterns(),
                no_commit_id=True,
                name_only=True,
                r=str(revision),
            ).splitlines()
        )
        intersection = files_in_revision.intersection(files_touched_in_branch)
        return Revision(count, str(revision), intersection)

    def checkout(self, branch_name: str):
        self._repo.git.checkout("-b", branch_name)

    def changes_between(self, base_revision: str, head_revision: str) -> list[Commit]:
        return list(
            reversed(
                list(
                    self._repo.iter_commits(
                        f"{base_revision}..{head_revision}", no_merges=True
                    )
                )
            )
        )

    def changes_in_branch(self) -> list[Revision]:
        base_ref = self.base_revision
        base_hex = (
            base_ref if base_ref else self._repo.git.rev_list("--max-parents=0", "HEAD")
        )

        head_hex = self._repo.active_branch.commit.hexsha
        logging.debug(
            f"Base reference: [bright_blue]{base_ref or '(grafted)'}[/bright_blue] [italic]{base_hex}[/italic]"
        )

        revisions = self.changes_between(base_hex, head_hex)

        logging.debug(
            f"Found {len(revisions)} revisions in branch: {[r.hexsha for r in revisions]}"
        )

        if not revisions:
            return []

        changed_files = list(
            itertools.chain.from_iterable(
                [
                    self._repo.git.diff_tree(
                        rev, name_only=True, no_commit_id=True, r=True
                    ).splitlines()
                    for rev in revisions
                ]
            )
        )

        return [
            self.__to_revision(count, rev, set(changed_files))
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
            f"{str(self._repo.head.commit)}..{str(parent_revs[0])}", name_only=True
        ).splitlines()
        return [Revision(ord=0, hash=str(self.get_sha), files_touched=files_changed)]

    def __get_remote(self) -> Remote:
        default_remote = self._repo.remote("origin")
        if "https:" not in default_remote.url or self._config.repo_credentials is None:
            return default_remote

        return default_remote.set_url(
            self._config.repo_credentials.to_url_with_credentials
        )

    def fetch_main_branch(self):
        remote = self.__get_remote()
        return remote.fetch(
            f"{self.main_branch}:refs/remotes/{self.main_origin_branch}"
        )

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
