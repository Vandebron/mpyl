""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
import logging
from typing import Optional

from ..project import Project, Dependencies
from ..project import Stage
from ..steps import ArtifactType
from ..steps.collection import StepsCollection
from ..steps.models import Output
from ..utilities.repo import Revision


def __log_invalidation(project: Project, stage: str, path: str, message: str) -> None:
    logging.debug(
        f"Invalidated '{project.name}' for '{stage}' by '{path}' because {message} "
    )


def __has_invalidated_dependencies(
    deps: Dependencies,
    project: Project,
    stage: str,
    path: str,
    steps: Optional[StepsCollection],
) -> bool:
    touched_stages: set[str] = {
        dep_stage
        for dep_stage, dependencies in deps.all().items()
        if len([d for d in dependencies if path.startswith(d)]) > 0
    }

    if stage in touched_stages:
        __log_invalidation(project, stage, path, "directly touched dependency")
        return True

    step_name = project.stages.for_stage(stage)
    if step_name is None or steps is None:
        return False

    executor = steps.get_executor(Stage(stage, "icon"), step_name)
    if executor is None:
        return False

    required_artifact = executor.required_artifact
    if required_artifact != ArtifactType.NONE:
        producing_stage = steps.get_stage_for_producing_artifact(
            project, required_artifact
        )
        if producing_stage is not None and producing_stage in touched_stages:
            __log_invalidation(
                project,
                stage,
                path,
                f"producing stage {producing_stage} for `{required_artifact}` ",
            )
            return True

    return False


def is_invalidated(
    project: Project, stage: str, path: str, steps: Optional[StepsCollection]
) -> bool:
    if path.startswith(project.root_path):
        __log_invalidation(project, stage, path, "is in project root")
        return True

    deps: Optional[Dependencies] = project.dependencies
    if deps is None:
        return False
    return __has_invalidated_dependencies(deps, project, stage, path, steps)


def output_invalidated(output: Optional[Output], revision_hash: str) -> bool:
    if output is None:
        return True
    if not output.success:
        return True
    if output.produced_artifact is None:
        return True
    artifact = output.produced_artifact
    if artifact.revision != revision_hash:
        return True

    return False


def _to_relevant_changes(
    project: Project, stage: str, change_history: list[Revision]
) -> set[str]:
    output: Output = Output.try_read(project.target_path, stage)
    relevant = set()
    for history in reversed(sorted(change_history, key=lambda c: c.ord)):
        if output_invalidated(output, history.hash):
            relevant.update(history.files_touched)
        else:
            return relevant

    return relevant


def _are_invalidated(
    project: Project,
    stage: str,
    change_history: list[Revision],
    steps: Optional[StepsCollection],
) -> bool:
    if project.stages.for_stage(stage) is None:
        return False

    relevant_changes = _to_relevant_changes(project, stage, change_history)
    changes = set(
        filter(lambda c: is_invalidated(project, stage, c, steps), relevant_changes)
    )
    return len(changes) > 0


def find_invalidated_projects_for_stage(
    all_projects: set[Project],
    stage: str,
    change_history: list[Revision],
    steps: Optional[StepsCollection],
) -> set[Project]:
    return set(
        filter(
            lambda p: _are_invalidated(p, stage, change_history, steps), all_projects
        )
    )


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))
