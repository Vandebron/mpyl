"""Simple MPyL build runner"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

from jsonschema import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from .cli import CliContext, MpylCliParameters
from .constants import RUN_ARTIFACTS_FOLDER
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
    logger = logging.getLogger("mpyl")

    # Write the run plan as a simple JSON file to be used by Github Actions
    simple_run_plan: dict[str, list[dict[str, Union[str, bool, list[str]]]]] = dict(
        {
            stage.name: [
                {
                    "service": project_execution.project.name,
                    "path": project_execution.project.path,
                    "base": project_execution.project.root_path,
                    "cached": project_execution.cached,
                    "maintainers": project_execution.project.maintainer,
                }
                for project_execution in project_executions
            ]
            for stage, project_executions in run_properties.run_plan.full_plan.items()
        }
    )
    run_plan_file = Path(RUN_ARTIFACTS_FOLDER) / "run_plan.json"
    os.makedirs(os.path.dirname(run_plan_file), exist_ok=True)
    with open(run_plan_file, "w", encoding="utf-8") as file:
        logger.info(f"Writing simple JSON run plan to: {run_plan_file}")
        json.dump(simple_run_plan, file)

    logger.info(f"MPyL log level is set to {run_properties.console.log_level}")

    result = RunResult(run_properties=run_properties)
    if result.has_projects_to_run(include_cached_projects=True):
        console.print(
            Markdown("**Execution plan:**  \n" + execution_plan_as_markdown(result))
        )
    else:
        logger.info("No changes detected, nothing to do.")


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

        if not run_result.has_projects_to_run(include_cached_projects=False):
            logger.info("Nothing to do. Exiting..")
            return run_result

        logger.info("Run plan:")
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
                logger=logger,
                accumulator=run_result,
                executor=steps,
                reporter=reporter,
                dry_run=cli_parameters.dryrun or cli_parameters.local,
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
    logger: logging.Logger,
    accumulator: RunResult,
    executor: Steps,
    reporter: Optional[Reporter] = None,
    dry_run: bool = True,
):
    try:
        for stage, project_executions in accumulator.run_plan.selected_plan.items():
            for project_execution in project_executions:
                if project_execution.cached:
                    logger.info(
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
                    logger.warning(f"Deployment failed for {project_execution.name}")
                    return accumulator

            if accumulator.failed_results:
                logger.warning(f"One of the builds failed at Stage {stage.name}")
                return accumulator
        return accumulator
    except ExecutionException as exc:
        accumulator.exception = exc
        return accumulator
