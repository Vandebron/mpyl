from pympl.project import Project
from pympl.projects.find import load_projects
from pympl.repo import Repository
from pympl.stage import Stage


def is_invalidated(project: Project, stage: Stage, path: str) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency = next(filter(lambda d: path.startswith(d), deps_for_stage), None) if deps else None
    startswith: bool = path.startswith(Project.to_project_root_path(project.path))
    return startswith or touched_dependency is not None


def are_invalidated(project: Project, stage: Stage, paths: set[str]) -> bool:
    return len(set(filter(lambda c: is_invalidated(project, stage, c), paths))) > 0


def find_invalidated_projects_for_stage(repository: Repository, stage: Stage, change_set: set[str]) -> set[Project]:
    projects = repository.find_projects()
    all_projects: set[Project] = set(load_projects(repository.root_dir(), projects))
    return set(filter(lambda p: are_invalidated(p, stage, change_set), all_projects))


def find_projects_for_stage(repository: Repository, stage: Stage) -> set[Project]:
    change_set = find_change_set_for_stage(repository, stage)
    return find_invalidated_projects_for_stage(repository, stage, change_set)


def find_change_set_for_stage(repository: Repository, stage: Stage) -> set[str]:
    if stage is Stage.BUILD or stage is Stage.TEST:
        return repository.changes_in_commit()
    return repository.changes_in_branch()
