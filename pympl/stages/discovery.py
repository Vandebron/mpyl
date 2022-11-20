from git import Repo

from pympl.project import Project
from pympl.projects.find import find_projects, repo_root


def find_invalidated_projects(change_set: set[str]):
    project_paths: set[str] = set(map(Project.to_project_root_path, find_projects()))
    projects_invalidated = set(
        filter(lambda p: next(filter(lambda c: c.startswith(p), change_set), None), project_paths))
    return projects_invalidated


def find_changes_in_branch() -> set[str]:
    repo = Repo(repo_root())
    return set(repo.git.diff('main', name_only=True).splitlines())


def find_changes_in_commit() -> set[str]:
    repo = Repo(repo_root())
    return set(repo.git.diff(None, name_only=True).splitlines())
