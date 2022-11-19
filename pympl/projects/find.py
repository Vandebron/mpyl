from git import Git
from pympl.project import Project, load_project


def find_projects() -> list[Project]:
    project_paths = Git().ls_files('**/deployment/project.yml').splitlines()
    return list(map(lambda p: load_project(p, False), project_paths))
