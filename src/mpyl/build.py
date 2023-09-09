"""Simple MPyL build runner"""

import logging
from pathlib import Path
from typing import Optional

from jsonschema import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from .cli import MpylCliParameters
from .project import load_project, Stage, Project
from .reporting.formatting.markdown import run_result_to_markdown
from .reporting.targets import Reporter
from .stages.discovery import for_stage, find_invalidated_projects_per_stage
from .steps.collection import StepsCollection
from .steps.models import RunProperties
from .steps.run import RunResult
from .steps.steps import Steps, ExecutionException
from .utilities.repo import Repository, RepoConfig, Revision


FORMAT = "%(name)s  %(message)s"


def get_build_plan(
    logger: logging.Logger,
    repo: Repository,
    run_properties: RunProperties,
    cli_parameters: MpylCliParameters,
) -> RunResult:
    tag = run_properties.versioning.tag
    if tag:
        changes = (
            repo.changes_in_tagged_commit(tag)
            if tag
            else repo.changes_in_merge_commit()
        )
    else:
        changes = (
            repo.changes_in_branch_including_local()
            if cli_parameters.local
            else repo.changes_in_branch()
        )
    logger.debug(f"Changes: {changes}")

    projects_per_stage: dict[Stage, set[Project]] = find_build_set(
        repo, changes, cli_parameters.all
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
            )

            if not run_plan.run_plan.items():
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
    repo: Repository, changes_in_branch: list[Revision], build_all: bool
) -> dict[Stage, set[Project]]:
    project_paths = repo.find_projects()
    all_projects = set(
        map(lambda p: load_project(Path(""), Path(p), False), project_paths)
    )

    if build_all:
        return {
            Stage.BUILD: for_stage(all_projects, Stage.BUILD),
            Stage.TEST: for_stage(all_projects, Stage.TEST),
            Stage.DEPLOY: for_stage(all_projects, Stage.DEPLOY),
            Stage.POST_DEPLOY: for_stage(all_projects, Stage.POST_DEPLOY),
        }

    return find_invalidated_projects_per_stage(all_projects, changes_in_branch)


def run_build(
    accumulator: RunResult,
    executor: Steps,
    reporter: Optional[Reporter] = None,
    dry_run: bool = True,
):
    try:
        for stage, projects in accumulator.run_plan.items():
            for proj in projects:
                result = executor.execute(stage, proj, dry_run)
                accumulator.append(result)
                if reporter:
                    reporter.send_report(accumulator)

                if not result.output.success and stage == Stage.DEPLOY:
                    logging.warning(f"Deployment failed for {proj.name}")
                    return accumulator

            if accumulator.failed_result:
                logging.warning(f"One of the builds failed at {stage}")
                return accumulator
        return accumulator
    except ExecutionException as exc:
        accumulator.exception = exc
        return accumulator
