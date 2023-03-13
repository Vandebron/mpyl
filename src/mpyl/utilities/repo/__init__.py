""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

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


class RepoConfig:
    main_branch: str

    def __init__(self, config: Dict):
        self.main_branch = config['cvs']['git']['mainBranch']


class Repository:

    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = Git().rev_parse('--show-toplevel')

    def __enter__(self):
        self._repo = Repo(self._root_dir)  # pylint: disable=attribute-defined-outside-init
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._repo.close()
        return self

    @property
    def get_sha(self):
        return self._repo.head.commit.hexsha

    @property
    def get_branch(self):
        return self._repo.active_branch.name

    def root_dir(self) -> Path:
        return Path(self._root_dir)

    def changes_in_branch(self) -> list[Revision]:
        revisions = reversed(list(self._repo.iter_commits(f"{self._config.main_branch}..HEAD")))
        return [Revision(count, str(rev),
                         self._repo.git.diff_tree(no_commit_id=True, name_only=True, r=str(rev)).splitlines()) for
                count, rev in enumerate(revisions)]

    def changes_in_branch_including_local(self) -> list[Revision]:
        in_branch = self.changes_in_branch()
        in_branch.append(Revision(len(in_branch), '', self.changes_in_commit()))
        return in_branch

    def pull_main_branch(self):
        remote = Remote(self._repo, 'origin')
        main = self._config.main_branch
        return remote.fetch(f"+refs/heads/{main}:refs/heads/{main}")

    def changes_in_commit(self) -> set[str]:
        changed: set[str] = set(self._repo.git.diff(None, name_only=True).splitlines())
        return changed.union(self._repo.untracked_files)

    def find_projects(self) -> set[str]:
        """ returns a set of all project.yml files """
        return set(self._repo.git.ls_files(f'**/{Project.project_yaml_path()}').splitlines())
