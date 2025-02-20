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

from ..constants import RUN_ARTIFACTS_FOLDER
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


def file_belongs_to_project(project: Project, path: str) -> bool:
    return Path(path).is_relative_to(project.root_path)


def is_file_in_project(logger: logging.Logger, project: Project, path: str) -> bool:
    if file_belongs_to_project(project, path):
        logger.debug(
            f"Project {project.name} added to the run plan because project file was modified: {path}"
        )
        return True
    return False


def is_file_a_dependency(
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
            f"Project {project.name} added to the run plan because a {stage} dependency was modified: {path}"
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
                f"Project {project.name} added to the run plan because producing stage {producing_stage} for required "
                f"artifact {required_artifact} is modified"
            )
            return True

    return False


def is_project_cached_for_stage(
    logger: logging.Logger,
    project: str,
    stage: str,
    output: Optional[Output],
    hashed_changes: Optional[str],
) -> bool:
    cached = False

    if stage == deploy.STAGE_NAME:
        logger.debug(
            f"Project {project} will execute stage {stage} because this stage is never cached"
        )
    elif output is None:
        logger.debug(
            f"Project {project} will execute stage {stage} because there is no previous run"
        )
    elif not output.success:
        logger.debug(
            f"Project {project} will execute stage {stage} because the previous run was not successful"
        )
    elif output.produced_artifact is None:
        logger.debug(
            f"Project {project} will execute stage {stage} because there was no artifact in the previous run"
        )
    elif not output.produced_artifact.hash:
        logger.debug(
            f"Project {project} will execute stage {stage} because there are no hashed changes for the previous run"
        )
    elif not hashed_changes:
        logger.debug(
            f"Project {project} will execute stage {stage} because there are no hashed changes for the current run"
        )
    elif output.produced_artifact.hash != hashed_changes:
        logger.debug(
            f"Project {project} will execute stage {stage} because its content changed since the previous run"
        )
        logger.debug(
            f"Hashed changes for the previous run: {output.produced_artifact.hash}"
        )
        logger.debug(f"Hashed changes for the current run:  {hashed_changes}")
    else:
        logger.debug(
            f"Project {project} will skip stage {stage} because its content did not change since the previous run"
        )
        logger.debug(f"Hashed changes for the current run: {hashed_changes}")
        cached = True

    return cached


def _hash_changes_in_project(
    project: Project,
    changeset: Changeset,
) -> Optional[str]:
    files_to_hash = {
        changed_file
        for changed_file in (changeset.files_touched(status={"A", "M", "R", "C"}))
        if file_belongs_to_project(project, changed_file)
        and Path(changed_file).is_file()
    }

    if len(files_to_hash) == 0:
        return None

    sha256 = hashlib.sha256()

    for changed_file in sorted(files_to_hash):
        with open(changed_file, "rb") as file:
            while True:
                data = file.read(65536)
                if not data:
                    break
                sha256.update(data)

    return sha256.hexdigest()


def to_project_executions(
    logger: logging.Logger,
    projects: set[Project],
    stage: str,
    changeset: Changeset,
) -> set[ProjectExecution]:
    def to_project_execution(
        project: Project,
    ) -> ProjectExecution:
        hashed_changes = _hash_changes_in_project(project=project, changeset=changeset)

        return ProjectExecution(
            project=project,
            changed_files=frozenset(changeset.files_touched()),
            hashed_changes=hashed_changes,
            cached=is_project_cached_for_stage(
                logger=logger,
                project=project.name,
                stage=stage,
                output=Output.try_read(project.target_path, stage),
                hashed_changes=hashed_changes,
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
    def build_project_execution(
        project: Project,
    ) -> Optional[ProjectExecution]:
        if project.stages.for_stage(stage) is None:
            return None

        is_any_dependency_modified = any(
            is_file_a_dependency(logger, project, stage, changed_file, steps)
            for changed_file in changeset.files_touched()
        )
        is_project_modified = any(
            is_file_in_project(logger, project, changed_file)
            for changed_file in changeset.files_touched()
        )

        if is_any_dependency_modified:
            logger.debug(
                f"Project {project.name} will execute stage {stage} because (at least) one of its dependencies was "
                f"modified"
            )

            if is_project_modified:
                hashed_changes = _hash_changes_in_project(
                    project=project, changeset=changeset
                )
            else:
                hashed_changes = None

            return ProjectExecution(
                project=project,
                changed_files=frozenset(changeset.files_touched()),
                hashed_changes=hashed_changes,
                cached=False,
            )

        if is_project_modified:
            hashed_changes = _hash_changes_in_project(
                project=project, changeset=changeset
            )

            return ProjectExecution(
                project=project,
                changed_files=frozenset(changeset.files_touched()),
                hashed_changes=hashed_changes,
                cached=is_project_cached_for_stage(
                    logger=logger,
                    project=project.name,
                    stage=stage,
                    output=Output.try_read(project.target_path, stage),
                    hashed_changes=hashed_changes,
                ),
            )

        return None

    return {
        project_execution
        for project_execution in map(build_project_execution, all_projects)
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
    changed_files_path: Optional[str] = None,
) -> RunPlan:
    run_plan_file = Path(RUN_ARTIFACTS_FOLDER) / "run_plan.pickle"

    existing_run_plan = _load_existing_run_plan(logger, run_plan_file)
    if existing_run_plan:
        logger.debug(f"Run plan: {existing_run_plan}")
        if selected_stage:
            existing_run_plan = existing_run_plan.select_stage(selected_stage)
            logger.info(f"Selected stage: {selected_stage.name}")
            logger.debug(f"Run plan: {existing_run_plan}")
        if selected_projects:
            existing_run_plan = existing_run_plan.select_projects(selected_projects)
            logger.info(f"Selected projects: {set(p.name for p in selected_projects)}")
            logger.debug(f"Run plan: {existing_run_plan}")
        return existing_run_plan

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
        changed_files_path=changed_files_path,
    )

    if not local:
        _store_run_plan(logger, run_plan, run_plan_file)
    return run_plan


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
    changed_files_path: Optional[str] = None,
) -> RunPlan:
    logger.info("Discovering run plan...")
    changeset = _get_changes(
        logger=logger,
        repo=repository,
        local=local,
        tag=tag,
        changed_files_path=changed_files_path,
    )

    plan = {}

    def add_projects_to_plan(stage: Stage):
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
        plan.update({stage: project_executions})

    if selected_stage:
        add_projects_to_plan(selected_stage)
    else:
        for stage in all_stages:
            add_projects_to_plan(stage)

    return RunPlan.from_plan(plan)


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return {p for p in projects if p.stages.for_stage(stage.name)}


def _get_changes(
    logger: logging.Logger,
    repo: Repository,
    local: bool,
    tag: Optional[str] = None,
    changed_files_path: Optional[str] = None,
) -> Changeset:
    if changed_files_path:
        return repo.changes_from_file(
            logger=logger, changed_files_path=changed_files_path
        )
    if local:
        return repo.changes_in_branch_including_local()
    if tag:
        return repo.changes_in_tagged_commit(logger=logger, tag=tag)

    return repo.changes_in_branch()


def _load_existing_run_plan(
    logger: logging.Logger,
    run_plan_file_path: Path,
) -> Optional[RunPlan]:
    if run_plan_file_path.is_file():
        logger.info(f"Loading existing run plan: {run_plan_file_path}")
        with open(run_plan_file_path, "rb") as file:
            return pickle.load(file)
    return None


def _store_run_plan(
    logger: logging.Logger,
    run_plan: RunPlan,
    run_plan_file_path: Path,
):
    os.makedirs(os.path.dirname(run_plan_file_path), exist_ok=True)
    with open(run_plan_file_path, "wb") as file:
        logger.info(f"Storing run plan in: {run_plan_file_path}")
        pickle.dump(run_plan, file, pickle.HIGHEST_PROTOCOL)
