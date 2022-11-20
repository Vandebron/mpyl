from pympl.project import Project
from pympl.repo import Repository


def find_invalidated_projects(repository: Repository, change_set: set[str]):
    project_paths: set[str] = set(map(Project.to_project_root_path, repository.find_projects()))
    projects_invalidated = set(
        filter(lambda p: next(filter(lambda c: c.startswith(p), change_set), None), project_paths))
    return projects_invalidated
