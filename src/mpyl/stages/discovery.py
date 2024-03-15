""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

from ..project import Project
from ..project import Stage
from ..project_execution import ProjectExecution
from ..steps import deploy
from ..steps.models import Output
from ..utilities.repo import Changeset


@dataclass(frozen=True)
class DeploySet:
    all_projects: set[Project]
    projects_to_deploy: set[Project]


def file_belongs_to_project(
    logger: logging.Logger, project: Project, path: str
) -> bool:
    startswith: bool = path.startswith(project.root_path)
    if startswith:
        logger.debug(
            f"Project {project.name}: {path} touched project root {project.root_path}"
        )
    return startswith


def is_dependency_touched(
    logger: logging.Logger, project: Project, stage: str, path: str
) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency = (
        next(filter(path.startswith, deps_for_stage), None) if deps else None
    )
    if touched_dependency:
        logger.debug(
            f"Project {project.name}: {path} touched dependency {touched_dependency}"
        )
    return touched_dependency is not None


def is_output_cached(output: Optional[Output], cache_key: str) -> bool:
    if (
        output is None
        or not output.success
        or output.produced_artifact is None
        or not output.produced_artifact.hash
    ):
        return False
    return output.produced_artifact.hash == cache_key


def hashed_changes(files: set[str]) -> str:
    sha256 = hashlib.sha256()

    for changed_file in sorted(files):
        with open(changed_file, "rb") as file:
            while True:
                data = file.read(65536)
                if not data:
                    break
                sha256.update(data)

    return sha256.hexdigest()


def _to_project_execution(
    logger: logging.Logger, project: Project, stage: str, changeset: Changeset
) -> Optional[ProjectExecution]:
    if project.stages.for_stage(stage) is None:
        return None

    is_any_dependency_touched = any(
        is_dependency_touched(logger, project, stage, changed_file)
        for changed_file in changeset.files_touched
    )
    project_changed_files = set(
        filter(
            lambda changed_file: file_belongs_to_project(logger, project, changed_file),
            changeset.files_touched,
        )
    )

    if project_changed_files:
        cache_key = hashed_changes(files=project_changed_files)
    elif is_any_dependency_touched:
        cache_key = changeset.sha
    else:
        return None

    if stage == deploy.STAGE_NAME:
        cached = False
    else:
        cached = is_output_cached(
            output=Output.try_read(project.target_path, stage),
            cache_key=cache_key,
        )

    return ProjectExecution(
        project=project,
        cache_key=cache_key,
        cached=cached,
    )


def build_project_executions(
    logger: logging.Logger,
    all_projects: set[Project],
    stage: str,
    changeset: Changeset,
) -> set[ProjectExecution]:
    maybe_execution_projects = set(
        map(
            lambda project: _to_project_execution(logger, project, stage, changeset),
            all_projects,
        )
    )
    return {
        project_execution
        for project_execution in maybe_execution_projects
        if project_execution is not None
    }


def find_build_set(
    logger: logging.Logger,
    all_projects: set[Project],
    changeset: Changeset,
    stages: list[Stage],
    build_all: bool,
    selected_stage: Optional[str] = None,
    selected_projects: Optional[str] = None,
) -> dict[Stage, set[ProjectExecution]]:
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
            project_executions = {ProjectExecution.always_run(p) for p in projects}
        else:
            project_executions = build_project_executions(
                logger, all_projects, stage.name, changeset
            )
            logger.debug(
                f"Invalidated projects for stage {stage.name}: {[p.name for p in project_executions]}"
            )

        build_set.update({stage: project_executions})

    return build_set


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))
