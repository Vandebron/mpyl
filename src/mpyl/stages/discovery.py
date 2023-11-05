""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
from typing import Optional

from ..project import Project
from ..project import Stage
from ..steps import ArtifactType
from ..steps.collection import StepsCollection
from ..steps.models import Output
from ..utilities.repo import Revision


def is_invalidated(
    project: Project, stage: str, path: str, steps: Optional[StepsCollection]
) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency_path = (
        next(filter(path.startswith, deps_for_stage), None) if deps else None
    )
    if touched_dependency_path is not None:
        return True

    if path.startswith(project.root_path):
        return True

    step_name = project.stages.for_stage(stage)

    touched = False
    if deps is not None:
        for dep_stage, all_deps in deps.all().items():
            if dep_stage != stage:
                continue
            for dep in all_deps:
                if path.startswith(dep):
                    touched = True
                    break

    if touched and steps and step_name is not None:
        executor = steps.get_executor(Stage(stage, "icon"), step_name)
        if executor is not None:
            required_artifact = executor.required_artifact
            if required_artifact != ArtifactType.NONE:
                producing_stage = steps.get_stage_for_producing_artifact(
                    project, required_artifact
                )
                if producing_stage is not None:
                    return True

    return False


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
