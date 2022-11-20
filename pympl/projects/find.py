from git import Git
from pympl.project import Project, load_project


def initialized_git() -> Git:
    return Git(Git().rev_parse('--show-toplevel'))


def find_projects() -> list[str]:
    return initialized_git().ls_files(f'**/{Project.project_yaml_path()}').splitlines()


def load_projects(paths: list[str]) -> list[Project]:
    return list(map(lambda p: load_project(p, False), paths))
