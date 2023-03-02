""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""

from ..project import Project
from ..project import Stage
from ..steps.models import Output
from ..utilities.repo import History


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


def find_invalidated_projects_for_stage(all_projects: set[Project], stage: Stage,
                                        change_history: list[History]) -> set[Project]:
    return set(filter(lambda p: are_invalidated(p, stage, change_history), all_projects))


def find_invalidated_projects_per_stage(all_projects: set[Project], change_history: list[History]) \
        -> dict[Stage, set[Project]]:
    projects_for_stage = {}
    for stage in Stage:
        projects = find_invalidated_projects_for_stage(all_projects, stage, change_history)
        if projects:
            projects_for_stage[stage] = projects
    return projects_for_stage


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage), projects))
