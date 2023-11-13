""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
import logging
from dataclasses import dataclass
from typing import Optional

from ..project import Project, Dependencies
from ..project import Stage
from ..steps import ArtifactType
from ..steps.collection import StepsCollection
from ..steps.models import Output
from ..utilities.repo import Revision


@dataclass(frozen=True)
class ChangedFile:
    path: str
    revision: str


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
    project: Project,
    stage: str,
    changed_file: ChangedFile,
    change_history: list[Revision],
    steps: Optional[StepsCollection],
) -> bool:
    invalidated_by_file = is_invalidated_by_file(project, stage, changed_file, steps)
    if invalidated_by_file:
        output = Output.try_read(project.target_path, stage)
        return _is_output_invalid(output, change_history, changed_file.revision)
    return False


def _is_output_invalid(
    output: Optional[Output], change_history: list[Revision], changed_file_revision: str
) -> bool:
    if output is None:
        return True
    if not output.success:
        return True

    artifact = output.produced_artifact
    if artifact is None:
        return True

    return _is_newer_than_artifact(
        artifact.revision, changed_file_revision, change_history
    )


def is_invalidated_by_file(
    project: Project,
    stage: str,
    changed_file: ChangedFile,
    steps: Optional[StepsCollection],
) -> bool:
    if changed_file.path.startswith(project.root_path):
        __log_invalidation(project, stage, changed_file.path, "is in project root")
        return True

    deps: Optional[Dependencies] = project.dependencies
    if deps is None:
        return False
    return __has_invalidated_dependencies(
        deps, project, stage, changed_file.path, steps
    )


def _is_newer_than_artifact(
    artifact_hash: str, file_hash: str, change_history: list[Revision]
):
    hashes = {rev.hash for rev in change_history}
    if artifact_hash not in hashes:
        return True

    for rev in sorted(change_history, key=lambda c: c.ord):
        if rev.hash == file_hash:
            return False
        if rev.hash == artifact_hash:
            return True
    return True


def _to_changed_files(change_history: list[Revision]) -> set[ChangedFile]:
    relevant = dict[str, str]()
    for history in sorted(change_history, key=lambda c: c.ord):
        latest = {path: history.hash for path in history.files_touched}
        relevant.update(latest)

    return {ChangedFile(path, revision) for path, revision in relevant.items()}


def _is_project_invalidated(
    project: Project,
    stage: str,
    change_history: list[Revision],
    steps: Optional[StepsCollection],
) -> bool:
    if project.stages.for_stage(stage) is None:
        return False

    changed_files = _to_changed_files(change_history)
    changes = set(
        filter(
            lambda c: is_invalidated(project, stage, c, change_history, steps),
            changed_files,
        )
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
            lambda p: _is_project_invalidated(p, stage, change_history, steps),
            all_projects,
        )
    )


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))
