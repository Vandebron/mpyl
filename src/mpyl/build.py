"""Simple MPyL build runner"""

import logging
from typing import Optional

from jsonschema import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from .cli import CliContext, MpylCliParameters
from .constants import DEFAULT_RUN_PROPERTIES_FILE_NAME
from .reporting.formatting.markdown import (
    execution_plan_as_markdown,
    run_result_to_markdown,
)
from .reporting.targets import Reporter
from .steps import deploy
from .steps.collection import StepsCollection
from .steps.models import RunProperties, Output
from .steps.run import RunResult
from .steps.run_properties import construct_run_properties
from .steps.steps import Steps, ExecutionException, StepResult


def print_status(
    obj: CliContext, cli_params: MpylCliParameters, explain_run_plan: bool
):
    run_properties = construct_run_properties(
        config=obj.config,
        properties=obj.run_properties,
        cli_parameters=cli_params,
        explain_run_plan=explain_run_plan,
    )
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
            f"`{main_branch}` at `{base_revision}`"
            if base_revision
            else f"not present. Earliest revision: `{obj.repo.root_commit_hex}` (grafted)."
        )
        console.print(
            Markdown(f"**Branch:** `{branch}`. Base {base_revision_specification}. ")
        )

    result = RunResult(run_properties=run_properties)
    if result.has_run_plan_projects:
        console.print(
            Markdown("**Execution plan:**  \n" + execution_plan_as_markdown(result))
        )
    else:
        console.print("No changes detected, nothing to do.")


FORMAT = "%(name)s  %(message)s"


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
        run_result = RunResult(run_properties=run_properties)

        if not run_result.has_run_plan_projects:
            logger.info("Nothing to do. Exiting..")
            return run_result

        logger.info("Build plan:")
        console.print(Markdown(f"\n\n{run_result_to_markdown(run_result)}"))

        if reporter:
            reporter.send_report(run_result)
        try:
            steps = Steps(
                logger=logger,
                properties=run_properties,
                steps_collection=StepsCollection(logger=logger),
            )

            run_result = run_build(
                run_result,
                steps,
                reporter,
                cli_parameters.dryrun or cli_parameters.local,
            )
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


def run_build(
    accumulator: RunResult,
    executor: Steps,
    reporter: Optional[Reporter] = None,
    dry_run: bool = True,
):
    try:
        for stage, project_executions in accumulator.run_plan.items():
            for project_execution in project_executions:
                if project_execution.cached:
                    logging.info(
                        f"Skipping {project_execution.name} for stage {stage.name} because it is cached"
                    )
                    result = StepResult(
                        stage=stage,
                        project=project_execution.project,
                        output=Output(success=True, message="This step was cached"),
                    )
                else:
                    result = executor.execute(stage.name, project_execution, dry_run)
                accumulator.append(result)
                if reporter:
                    reporter.send_report(accumulator)

                if not result.output.success and stage.name == deploy.STAGE_NAME:
                    logging.warning(f"Deployment failed for {project_execution.name}")
                    return accumulator

            if accumulator.failed_results:
                logging.warning(f"One of the builds failed at Stage {stage.name}")
                return accumulator
        return accumulator
    except ExecutionException as exc:
        accumulator.exception = exc
        return accumulator
