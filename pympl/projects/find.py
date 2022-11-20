from git import Git
from pympl.project import Project, load_project


def repo_root() -> str:
    return Git().rev_parse('--show-toplevel')


def find_projects() -> list[str]:
    return Git(repo_root()).ls_files(f'**/{Project.project_yaml_path()}').splitlines()


def load_projects(paths: list[str]) -> list[Project]:
    return list(map(lambda p: load_project(f'{repo_root()}/{p}', False), paths))
