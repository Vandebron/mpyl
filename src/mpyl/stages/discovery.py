""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
import logging
from dataclasses import dataclass
from typing import Optional

from ..project import Project
from ..project import Stage
from ..steps import deploy
from ..steps.models import Output
from ..utilities.repo import Revision


@dataclass(frozen=True)
class DeploySet:
    all_projects: set[Project]
    projects_to_deploy: set[Project]


def is_invalidated(
    logger: logging.Logger, project: Project, stage: str, path: str
) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency = (
        next(filter(path.startswith, deps_for_stage), None) if deps else None
    )
    startswith: bool = path.startswith(project.root_path)
    if touched_dependency:
        logger.debug(
            f"Project {project.name}: {path} touched dependency {touched_dependency}"
        )
    if startswith:
        logger.debug(
            f"Project {project.name}: {path} touched project root {project.root_path}"
        )
    return startswith or touched_dependency is not None


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
        if stage == deploy.STAGE_NAME or output_invalidated(output, history.hash):
            relevant.update(history.files_touched)
        else:
            return relevant

    return relevant


def _are_invalidated(
    logger: logging.Logger, project: Project, stage: str, change_history: list[Revision]
) -> bool:
    if project.stages.for_stage(stage) is None:
        return False

    relevant_changes = _to_relevant_changes(project, stage, change_history)
    return (
        len(
            set(
                filter(
                    lambda c: is_invalidated(logger, project, stage, c),
                    relevant_changes,
                )
            )
        )
        > 0
    )


def find_invalidated_projects_for_stage(
    logger: logging.Logger,
    all_projects: set[Project],
    stage: str,
    change_history: list[Revision],
) -> set[Project]:
    return set(
        filter(
            lambda p: _are_invalidated(logger, p, stage, change_history),
            all_projects,
        )
    )


def find_build_set(
    logger: logging.Logger,
    all_projects: set[Project],
    changes_in_branch: list[Revision],
    stages: list[Stage],
    build_all: bool,
    selected_stage: Optional[str] = None,
    selected_projects: Optional[str] = None,
) -> dict[Stage, set[Project]]:
    if selected_projects:
        projects_list = selected_projects.split(",")

    build_set = {}

    for stage in stages:
        if selected_stage and selected_stage != stage.name:
            continue

        if build_all or selected_projects:
            if selected_projects:
                all_projects = set(
                    filter(lambda p: p.name in projects_list, all_projects)
                )
            projects = for_stage(all_projects, stage)
        else:
            projects = find_invalidated_projects_for_stage(
                logger, all_projects, stage.name, changes_in_branch
            )
            logger.debug(
                f"Invalidated projects for stage {stage.name}: {[p.name for p in projects]}"
            )

        build_set.update({stage: projects})

    return build_set


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))
