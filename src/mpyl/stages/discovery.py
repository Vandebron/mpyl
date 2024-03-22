""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""

import hashlib
import logging
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..constants import BUILD_ARTIFACTS_FOLDER
from ..project import Project
from ..project import Stage
from ..project_execution import ProjectExecution
from ..steps import deploy
from ..steps.collection import StepsCollection
from ..steps.models import Output, ArtifactType
from ..utilities.repo import Changeset, Repository


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
    logger: logging.Logger,
    project: Project,
    stage: str,
    path: str,
    steps: Optional[StepsCollection],
) -> bool:
    deps = project.dependencies
    if not deps:
        return False

    touched_stages: set[str] = {
        dep_stage
        for dep_stage, dependencies in deps.all().items()
        if len([d for d in dependencies if path.startswith(d)]) > 0
    }

    if stage in touched_stages:
        logger.debug(
            f"Project {project.name}: {path} touched one of the dependencies for stage {stage}"
        )
        return True

    step_name = project.stages.for_stage(stage)
    if step_name is None or steps is None:
        logger.debug(
            f"Project {project.name}: the step for stage {stage} is not defined or not found"
        )
        return False

    executor = steps.get_executor(Stage(stage, "icon"), step_name)
    if executor is None:
        logger.debug(f"Project {project.name}: no executor found for stage {stage}")
        return False

    required_artifact = executor.required_artifact
    if required_artifact != ArtifactType.NONE:
        producing_stage = steps.get_stage_for_producing_artifact(
            project, required_artifact
        )
        if producing_stage is not None and producing_stage in touched_stages:
            logger.debug(
                f"Project {project.name}: producing stage {producing_stage} for required artifact {required_artifact} "
                f"is touched"
            )
            return True

    return False


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
    logger: logging.Logger,
    project: Project,
    stage: str,
    changes: Changeset,
    steps: Optional[StepsCollection],
) -> Optional[ProjectExecution]:
    if project.stages.for_stage(stage) is None:
        return None

    is_any_dependency_touched = any(
        is_dependency_touched(logger, project, stage, changed_file, steps)
        for changed_file in changes.files_touched()
    )
    is_project_modified = any(
        file_belongs_to_project(logger, project, changed_file)
        for changed_file in changes.files_touched()
    )

    if is_project_modified:
        files_to_hash = set(
            filter(
                lambda changed_file: file_belongs_to_project(
                    logger, project, changed_file
                ),
                changes.files_touched(status={"A", "M", "R"}),
            )
        )

        if len(files_to_hash) == 0:
            cache_key = changes.sha
        else:
            cache_key = hashed_changes(files=files_to_hash)
    elif is_any_dependency_touched:
        cache_key = changes.sha
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
    changes: Changeset,
    steps: Optional[StepsCollection],
) -> set[ProjectExecution]:
    maybe_execution_projects = set(
        map(
            lambda project: _to_project_execution(
                logger, project, stage, changes, steps
            ),
            all_projects,
        )
    )
    return {
        project_execution
        for project_execution in maybe_execution_projects
        if project_execution is not None
    }


def find_build_set(  # pylint: disable=too-many-arguments, too-many-locals
    logger: logging.Logger,
    repository: Repository,
    all_projects: set[Project],
    stages: list[Stage],
    build_all: bool,
    local: bool,
    tag: Optional[str] = None,
    selected_stage: Optional[str] = None,
    selected_projects: Optional[str] = None,
    sequential: Optional[bool] = False,
) -> dict[Stage, set[ProjectExecution]]:
    if selected_projects:
        projects_list = selected_projects.split(",")

    build_set: dict[Stage, set[ProjectExecution]] = {}

    build_set_file = Path(BUILD_ARTIFACTS_FOLDER) / "build_plan"
    if sequential and not build_all and not selected_projects:
        if not build_set_file.is_file():
            logger.warning(
                f"Sequential flag is passed, but no previous build set found: {build_set_file}"
            )
        else:
            logger.info(f"Loading cached build set: {build_set_file}")
            return _get_cached_build_set(
                build_set_file=build_set_file, selected_stage=selected_stage
            )

    elif build_set_file.is_file():
        logger.info(f"Deleting previous build set: {build_set_file}")
        build_set_file.unlink()

    logger.info("Discovering build set...")
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
            steps = StepsCollection(logger=logging.getLogger())
            changes_in_branch = (
                _get_changes(repository, local, tag)
                if not selected_projects or build_all
                else []
            )

            project_executions = build_project_executions(
                logger, all_projects, stage.name, changes_in_branch, steps
            )
            logger.debug(
                f"Invalidated projects for stage {stage.name}: {[p.name for p in project_executions]}"
            )

        build_set.update({stage: project_executions})

    if not selected_stage and not build_all and not selected_projects:
        os.makedirs(os.path.dirname(build_set_file), exist_ok=True)
        with open(build_set_file, "wb") as file:
            logger.info(f"Storing build set in: {build_set_file}")
            pickle.dump(build_set, file, pickle.HIGHEST_PROTOCOL)

    return build_set


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))


def _get_changes(repo: Repository, local: bool, tag: Optional[str] = None):
    if local:
        return repo.changes_in_branch_including_local()
    if tag:
        return repo.changes_in_tagged_commit(tag)

    return repo.changes_in_branch()


def _get_cached_build_set(
    build_set_file: Path, selected_stage: Optional[str]
) -> dict[Stage, set[ProjectExecution]]:
    with open(build_set_file, "rb") as file:
        full_build_set: dict[Stage, set[ProjectExecution]] = pickle.load(file)
        if selected_stage:
            return {
                stage: project_executions
                for stage, project_executions in full_build_set.items()
                if stage.name == selected_stage
            }
        return full_build_set
