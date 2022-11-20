from pympl.project import Project
from pympl.repo import Repository
from pympl.stages import Stage


def find_invalidated_projects(repository: Repository, change_set: set[str]):
    project_paths: set[str] = set(map(Project.to_project_root_path, repository.find_projects()))
    projects_invalidated = set(
        filter(lambda p: next(filter(lambda c: c.startswith(p), change_set), None), project_paths))
    return projects_invalidated


def find_projects_for_stage(repository: Repository, stage: Stage) -> set[str]:
    change_set = find_change_set_for_stage(repository, stage)
    return find_invalidated_projects(repository, change_set)


def find_change_set_for_stage(repository: Repository, stage: Stage) -> set[str]:
    if stage is Stage.BUILD or stage is Stage.TEST:
        return repository.changes_in_commit()
    return repository.changes_in_branch()
