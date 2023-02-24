""" Defines information about the repository, any changes made to it and the containing projects.
`mpyl.utilities.repo.Repository` is a facade for the Version Control System.
At this moment Git is the only supported VCS.
"""

from dataclasses import dataclass
from typing import Dict

from git import Git, Repo
from ...project import Project


@dataclass(frozen=True)
class History:
    ord: int
    revision: str
    files_touched: set[str]


class RepoConfig:
    main_branch: str

    def __init__(self, config: Dict):
        self.main_branch = config['cvs']['git']['mainBranch']


class Repository:

    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = Git().rev_parse('--show-toplevel')
        self._repo = Repo(self._root_dir)

    @property
    def get_sha(self):
        return self._repo.head.commit.hexsha

    @property
    def get_branch(self):
        return self._repo.active_branch.name

    def root_dir(self) -> str:
        return self._root_dir

    def changes_in_branch(self) -> list[History]:
        revisions = reversed(list(self._repo.iter_commits(f"{self._config.main_branch}..HEAD")))
        return [History(count, str(rev),
                        self._repo.git.diff_tree(no_commit_id=True, name_only=True, r=str(rev)).splitlines()) for
                count, rev in enumerate(revisions)]

    def changes_in_commit(self) -> set[str]:
        return set(self._repo.git.diff(None, name_only=True).splitlines())

    def find_projects(self) -> set[str]:
        """ returns a set of all project.yml files """
        return set(self._repo.git.ls_files(f'**/{Project.project_yaml_path()}').splitlines())
