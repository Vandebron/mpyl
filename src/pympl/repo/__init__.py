from git import Git, Repo
from pympl.project import Project


class Repository:

    def __init__(self, main_branch):
        self._main_branch = main_branch
        self._root_dir = Git().rev_parse('--show-toplevel')
        self._repo = Repo(self._root_dir)

    def root_dir(self) -> str:
        return self._root_dir

    def changes_in_branch(self) -> set[str]:
        return set(self._repo.git.diff(self._main_branch, name_only=True).splitlines())

    def changes_in_commit(self) -> set[str]:
        return set(self._repo.git.diff(None, name_only=True).splitlines())

    def find_projects(self) -> set[str]:
        return set(self._repo.git.ls_files(f'**/{Project.project_yaml_path()}').splitlines())
