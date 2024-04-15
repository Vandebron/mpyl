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
from ..run_plan import RunPlan
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


def is_dependency_modified(
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


def is_project_cached_for_stage(
    logger: logging.Logger,
    project: str,
    stage: str,
    output: Optional[Output],
    cache_key: str,
) -> bool:
    cached = False

    if stage == deploy.STAGE_NAME:
        logger.debug(
            f"Project {project} will execute stage {stage} again because this stage is never cached"
        )
    elif output is None:
        logger.debug(
            f"Project {project} will execute stage {stage} again because there is no previous run"
        )
    elif not output.success:
        logger.debug(
            f"Project {project} will execute stage {stage} again because the previous run was not successful"
        )
    elif output.produced_artifact is None:
        logger.debug(
            f"Project {project} will execute stage {stage} again because there was no artifact in the previous run"
        )
    elif not output.produced_artifact.hash:
        logger.debug(
            f"Project {project} will execute stage {stage} again because there is no cache key in the previous run"
        )
    elif output.produced_artifact.hash != cache_key:
        logger.debug(
            f"Project {project} will execute stage {stage} again because its content changed since the previous run"
        )
        logger.debug(
            f"Hash of contents for previous run: {output.produced_artifact.hash}"
        )
        logger.debug(f"Hash of contents for current run:  {cache_key}")
    else:
        logger.debug(
            f"Project {project} will skip stage {stage} because its content did not change since the previous run"
        )
        logger.debug(f"Hash of contents for current run: {cache_key}")
        cached = True

    return cached


def _cache_key_from_changes_in_project(
    logger: logging.Logger,
    project: Project,
    changeset: Changeset,
):
    files_to_hash = set(
        filter(
            lambda changed_file: file_belongs_to_project(logger, project, changed_file),
            changeset.files_touched(status={"A", "M", "R"}),
        )
    )

    if len(files_to_hash) == 0:
        cache_key = changeset.sha
        logger.debug(
            f"Project {project.name}: no content changes, falling back to git revision as cache key: {cache_key}"
        )
    else:
        sha256 = hashlib.sha256()

        for changed_file in sorted(files_to_hash):
            with open(changed_file, "rb") as file:
                while True:
                    data = file.read(65536)
                    if not data:
                        break
                    sha256.update(data)

        cache_key = sha256.hexdigest()
        logger.debug(
            f"Project {project.name}: using hash of modified files as cache key {cache_key}"
        )

    return cache_key


def to_project_executions(
    logger: logging.Logger,
    projects: set[Project],
    stage: str,
    changeset: Changeset,
) -> set[ProjectExecution]:
    def to_project_execution(
        project: Project,
    ) -> ProjectExecution:
        cache_key = _cache_key_from_changes_in_project(
            logger=logger, project=project, changeset=changeset
        )
        return ProjectExecution(
            project=project,
            cache_key=cache_key,
            cached=is_project_cached_for_stage(
                logger=logger,
                project=project.name,
                stage=stage,
                output=Output.try_read(project.target_path, stage),
                cache_key=cache_key,
            ),
        )

    return set(map(to_project_execution, projects))


def find_projects_to_execute(
    logger: logging.Logger,
    all_projects: set[Project],
    stage: str,
    changeset: Changeset,
    steps: Optional[StepsCollection],
) -> set[ProjectExecution]:
    def project_execution_if_needed(
        project: Project,
    ) -> Optional[ProjectExecution]:
        if project.stages.for_stage(stage) is None:
            return None

        is_any_dependency_modified = any(
            is_dependency_modified(logger, project, stage, changed_file, steps)
            for changed_file in changeset.files_touched()
        )
        is_project_modified = any(
            file_belongs_to_project(logger, project, changed_file)
            for changed_file in changeset.files_touched()
        )

        if is_project_modified:
            cache_key = _cache_key_from_changes_in_project(
                logger=logger, project=project, changeset=changeset
            )

        elif is_any_dependency_modified:
            cache_key = changeset.sha
            logger.debug(
                f"Project {project.name}: using git revision as cache key: {cache_key}"
            )
        else:
            return None

        return ProjectExecution(
            project=project,
            cache_key=cache_key,
            cached=is_project_cached_for_stage(
                logger=logger,
                project=project.name,
                stage=stage,
                output=Output.try_read(project.target_path, stage),
                cache_key=cache_key,
            ),
        )

    return {
        project_execution
        for project_execution in map(project_execution_if_needed, all_projects)
        if project_execution is not None
    }


# pylint: disable=too-many-arguments
def create_run_plan(
    logger: logging.Logger,
    repository: Repository,
    all_projects: set[Project],
    all_stages: list[Stage],
    build_all: bool,
    local: bool,
    selected_projects: set[Project],
    tag: Optional[str] = None,
    selected_stage: Optional[Stage] = None,
) -> RunPlan:
    run_plan_file = Path(BUILD_ARTIFACTS_FOLDER) / "build_plan"

    existing_run_plan = _load_cached_run_plan(logger, run_plan_file)
    if existing_run_plan:
        return _filter_existing_run_plan(
            run_plan=existing_run_plan,
            selected_stage=selected_stage,
            selected_projects=selected_projects,
        )

    run_plan = _discover_run_plan(
        logger=logger,
        repository=repository,
        all_projects=all_projects,
        all_stages=all_stages,
        build_all=build_all,
        local=local,
        selected_projects=selected_projects,
        selected_stage=selected_stage,
        tag=tag,
    )

    _store_run_plan(logger, run_plan, run_plan_file)
    return run_plan


def _filter_existing_run_plan(
    run_plan: RunPlan,
    selected_stage: Optional[Stage],
    selected_projects: set[Project],
) -> RunPlan:
    filtered_run_plan = run_plan

    if selected_stage:
        filtered_run_plan = filtered_run_plan.for_stage(selected_stage)

    if selected_projects:
        filtered_run_plan = filtered_run_plan.for_projects(selected_projects)

    return filtered_run_plan


# pylint: disable=too-many-arguments
def _discover_run_plan(
    logger: logging.Logger,
    repository: Repository,
    all_projects: set[Project],
    all_stages: list[Stage],
    build_all: bool,
    local: bool,
    selected_projects: set[Project],
    selected_stage: Optional[Stage],
    tag: Optional[str] = None,
) -> RunPlan:
    logger.info("Discovering run plan...")
    run_plan: RunPlan = RunPlan.empty()
    changeset = _get_changes(repository, local, tag)

    for stage in all_stages:
        if selected_stage and stage != selected_stage:
            continue

        if build_all:
            project_executions = to_project_executions(
                logger=logger,
                projects=for_stage(all_projects, stage),
                stage=stage.name,
                changeset=changeset,
            )
        elif selected_projects:
            project_executions = to_project_executions(
                logger=logger,
                projects=for_stage(selected_projects, stage),
                stage=stage.name,
                changeset=changeset,
            )
        else:
            project_executions = find_projects_to_execute(
                logger=logger,
                all_projects=all_projects,
                stage=stage.name,
                changeset=changeset,
                steps=StepsCollection(logger=logging.getLogger()),
            )

        logger.debug(
            f"Will execute projects for stage {stage.name}: {[p.name for p in project_executions]}"
        )
        run_plan.add_stage(stage, project_executions)

    return run_plan


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return {p for p in projects if p.stages.for_stage(stage.name)}


def _get_changes(repo: Repository, local: bool, tag: Optional[str] = None):
    if local:
        return repo.changes_in_branch_including_local()
    if tag:
        return repo.changes_in_tagged_commit(tag)

    return repo.changes_in_branch()


def _load_cached_run_plan(
    logger: logging.Logger,
    run_plan_file: Path,
) -> Optional[RunPlan]:
    if run_plan_file.is_file():
        logger.info(f"Loading cached run plan: {run_plan_file}")
        with open(run_plan_file, "rb") as file:
            return pickle.load(file)
    return None


def _store_run_plan(
    logger: logging.Logger,
    run_plan: RunPlan,
    run_plan_file: Path,
):
    os.makedirs(os.path.dirname(run_plan_file), exist_ok=True)
    with open(run_plan_file, "wb") as file:
        logger.info(f"Storing run plan in: {run_plan_file}")
        pickle.dump(run_plan, file, pickle.HIGHEST_PROTOCOL)
