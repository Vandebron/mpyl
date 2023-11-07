"""Simple MPyL build runner"""

import logging
from pathlib import Path
from typing import Optional

from jsonschema import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from .cli import CliContext, MpylCliParameters
from .constants import DEFAULT_RUN_PROPERTIES_FILE_NAME
from .project import Stage, Project, load_project
from .reporting.formatting.markdown import (
    execution_plan_as_markdown,
    run_result_to_markdown,
)
from .reporting.targets import Reporter
from .stages.discovery import for_stage, find_invalidated_projects_for_stage
from .steps import deploy
from .steps.collection import StepsCollection
from .steps.models import RunProperties
from .steps.run import RunResult
from .steps.steps import Steps, ExecutionException
from .utilities.repo import Revision, Repository, RepoConfig


def print_status(obj: CliContext, cli_params: MpylCliParameters):
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    console = obj.console
    console.print(f"MPyL log level is set to {run_properties.console.log_level}")

    branch = obj.repo.get_branch
    main_branch = obj.repo.main_branch
    tag = run_properties.versioning.tag

    if tag is None:
        if run_properties.versioning.branch and not obj.repo.get_branch:
            console.print("Current branch is detached.")
        else:
            console.log(
                Markdown(
                    f"Branch not specified at `build.versioning.branch` in _{DEFAULT_RUN_PROPERTIES_FILE_NAME}_, "
                    f"falling back to git: _{obj.repo.get_branch}_"
                )
            )

        if branch == main_branch:
            console.log(f"On main branch ({branch}), cannot determine build status")
            return

    version = run_properties.versioning
    revision = version.revision or obj.repo.get_sha
    base_revision = obj.repo.base_revision
    if tag:
        console.print(Markdown(f"**Tag:** `{version.tag}` at `{revision}`. "))
    else:
        base_revision_specification = (
            f"at `{base_revision}`"
            if base_revision
            else f"not present. Earliest revision: `{obj.repo.root_commit_hex}` (grafted)."
        )
        console.print(
            Markdown(f"**Branch:** `{branch}`. Base {base_revision_specification}. ")
        )

    result = get_build_plan(
        logger=logging.getLogger("mpyl"),
        repo=obj.repo,
        run_properties=run_properties,
        cli_parameters=cli_params,
    )
    if result.has_run_plan_projects:
        console.print(
            Markdown("**Execution plan:**  \n" + execution_plan_as_markdown(result))
        )
    else:
        console.print("No changes detected, nothing to do.")


FORMAT = "%(name)s  %(message)s"


def get_build_plan(
    logger: logging.Logger,
    repo: Repository,
    run_properties: RunProperties,
    cli_parameters: MpylCliParameters,
    safe_load_projects: bool = False,
) -> RunResult:
    tag = run_properties.versioning.tag

    changes = (
        repo.changes_in_branch_including_local()
        if cli_parameters.local
        else (repo.changes_in_tagged_commit(tag) if tag else repo.changes_in_branch())
    )
    logger.debug(f"Changes: {changes}")

    projects_per_stage: dict[Stage, set[Project]] = find_build_set(
        repo,
        changes,
        run_properties.stages,
        cli_parameters.all,
        safe_load_projects,
        cli_parameters.stage,
        cli_parameters.projects,
    )
    return RunResult(
        run_properties=run_properties,
        run_plan=projects_per_stage,
    )


def run_mpyl(
    run_properties: RunProperties,
    cli_parameters: MpylCliParameters,
    reporter: Optional[Reporter],
) -> RunResult:
    console_properties = run_properties.console
    console = Console(
        markup=False,
        width=None if cli_parameters.local else console_properties.width,
        no_color=False,
        log_path=False,
        color_system="256",
    )
    logging.raiseExceptions = False
    log_level = "DEBUG" if cli_parameters.verbose else console_properties.log_level
    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[
            RichHandler(markup=False, console=console, show_path=cli_parameters.local)
        ],
    )
    print(f"Log level is set to {log_level}")
    logger = logging.getLogger("mpyl")
    try:
        with Repository(RepoConfig.from_config(run_properties.config)) as repo:
            run_plan = get_build_plan(
                logger=logger,
                repo=repo,
                run_properties=run_properties,
                cli_parameters=cli_parameters,
                safe_load_projects=True,
            )

            if not run_plan.has_run_plan_projects:
                logger.info("Nothing to do. Exiting..")
                return run_plan

            logger.info("Build plan:")
            console.print(Markdown(f"\n\n{run_result_to_markdown(run_plan)}"))

            run_result: RunResult = run_plan
            if reporter:
                reporter.send_report(run_plan)
            try:
                steps = Steps(
                    logger=logger,
                    properties=run_properties,
                    steps_collection=StepsCollection(logger=logger),
                )
                run_result = run_build(run_plan, steps, reporter, cli_parameters.local)
            except ValidationError as exc:
                console.log(
                    f'Schema validation failed {exc.message} at `{".".join(map(str, exc.path))}`'
                )
                raise exc
            except ExecutionException as exc:
                run_result.exception = exc
                console.log(f"Exception during build execution: {exc}")
                console.print_exception()

            console.print(Markdown(run_result_to_markdown(run_result)))
            return run_result

    except Exception as exc:
        console.log(f"Unexpected exception: {exc}")
        console.print_exception()
        raise exc


def find_build_set(
    repo: Repository,
    changes_in_branch: list[Revision],
    stages: list[Stage],
    build_all: bool,
    safe_load_projects: bool,
    selected_stage: Optional[str] = None,
    selected_projects: Optional[str] = None,
) -> dict[Stage, set[Project]]:
    project_paths = repo.find_projects()
    all_projects = set(
        map(
            lambda p: load_project(
                root_dir=Path(""),
                project_path=Path(p),
                strict=False,
                log=True,
                safe=safe_load_projects,
            ),
            project_paths,
        )
    )
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
                all_projects, stage.name, changes_in_branch
            )

        build_set.update({stage: projects})

    return build_set


def run_build(
    accumulator: RunResult,
    executor: Steps,
    reporter: Optional[Reporter] = None,
    dry_run: bool = True,
):
    try:
        for stage, projects in accumulator.run_plan.items():
            for proj in projects:
                result = executor.execute(stage.name, proj, dry_run)
                accumulator.append(result)
                if reporter:
                    reporter.send_report(accumulator)

                if not result.output.success and stage.name == deploy.STAGE_NAME:
                    logging.warning(f"Deployment failed for {proj.name}")
                    return accumulator

            if accumulator.failed_result:
                logging.warning(f"One of the builds failed at Stage {stage.name}")
                return accumulator
        return accumulator
    except ExecutionException as exc:
        accumulator.exception = exc
        return accumulator
