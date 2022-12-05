from typing import Dict

from git import Git, Repo
from ..project import Project


class RepoConfig:
    main_branch: str

    def __init__(self, config: Dict):
        self.main_branch = config['cvs']['git']['main_branch']


class Repository:

    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = Git().rev_parse('--show-toplevel')
        self._repo = Repo(self._root_dir)

    def root_dir(self) -> str:
        return self._root_dir

    def changes_in_branch(self) -> set[str]:
        return set(self._repo.git.diff(self._config.main_branch, name_only=True).splitlines())

    def changes_in_commit(self) -> set[str]:
        return set(self._repo.git.diff(None, name_only=True).splitlines())

    def find_projects(self) -> set[str]:
        return set(self._repo.git.ls_files(f'**/{Project.project_yaml_path()}').splitlines())
