from ..project import Project
from ..projects.find import load_projects
from ..repo import History, Repository
from ..stage import Stage
from ..steps.models import Output


def is_invalidated(project: Project, stage: Stage, path: str) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency = next(filter(path.startswith, deps_for_stage), None) if deps else None
    startswith: bool = path.startswith(project.root_path)
    return startswith or touched_dependency is not None


def _to_relevant_changes(project: Project, stage: Stage, change_history: list[History]) -> set[str]:
    output: Output = Output.try_read(project.target_path, stage)
    relevant = set()
    for history in reversed(sorted(change_history, key=lambda c: c.ord)):
        if stage == Stage.DEPLOY or output is None or output.produced_artifact is None \
                or output.produced_artifact.revision != history.revision:
            relevant.update(history.files_touched)
        else:
            return relevant

    return relevant


def are_invalidated(project: Project, stage: Stage, change_history: list[History]) -> bool:
    if project.stages.for_stage(stage) is None:
        return False

    relevant_changes = _to_relevant_changes(project, stage, change_history)
    return len(set(filter(lambda c: is_invalidated(project, stage, c), relevant_changes))) > 0


def find_invalidated_projects_for_stage(repository: Repository, stage: Stage,
                                        change_history: list[History]) -> set[Project]:
    projects = repository.find_projects()
    all_projects: set[Project] = set(load_projects(repository.root_dir(), projects))
    return set(filter(lambda p: are_invalidated(p, stage, change_history), all_projects))


def find_projects_for_stage(repository: Repository, stage: Stage) -> set[Project]:
    change_set = repository.changes_in_branch()
    return find_invalidated_projects_for_stage(repository, stage, change_set)
