"""Simple MPyL build runner"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from ....project import load_project, Stage, Project
from ....reporting.formatting.markdown import run_result_to_markdown
from ....reporting.targets import Reporter
from ....stages.discovery import for_stage, find_invalidated_projects_per_stage
from ....steps.models import RunProperties
from ....steps.run import RunResult
from ....steps.steps import Steps
from ....utilities.repo import Repository, RepoConfig


@dataclass(frozen=True)
class MpylRunConfig:
    config: dict
    run_properties: RunProperties


@dataclass(frozen=True)
class MpylCliParameters:
    local: bool
    verbose: bool = False
    all: bool = False


@dataclass(frozen=True)
class MpylRunParameters:
    run_config: MpylRunConfig
    parameters: MpylCliParameters


FORMAT = "%(name)s  %(message)s"


def get_build_plan(logger: logging.Logger, repo: Repository, mpyl_run_parameters: MpylRunParameters) -> RunResult:
    params = mpyl_run_parameters.parameters
    logger.info(f"Running with {params}")
    if not params.local:
        pull_result = repo.pull_main_branch()
        logger.info(f'Pulled `{pull_result[0].remote_ref_path.strip()}` to local')

    changes_in_branch = repo.changes_in_branch_including_local() if params.local else repo.changes_in_branch()
    logger.debug(f'Changes: {changes_in_branch}')

    projects_per_stage: dict[Stage, set[Project]] = find_build_set(repo, changes_in_branch, params.all)
    return RunResult(run_properties=mpyl_run_parameters.run_config.run_properties, run_plan=projects_per_stage)


def run_mpyl(mpyl_run_parameters: MpylRunParameters, reporter: Optional[Reporter]) -> RunResult:
    params = mpyl_run_parameters.parameters
    console = Console(markup=True, width=None if params.local else 135, no_color=False, log_path=False,
                      color_system='256')
    logging.basicConfig(
        level="DEBUG" if params.verbose else "INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True,
                              console=console, show_path=params.local)]
    )
    logger = logging.getLogger('mpyl')
    try:
        with Repository(RepoConfig(mpyl_run_parameters.run_config.config)) as repo:

            run_plan = get_build_plan(logger, repo, mpyl_run_parameters)

            if not run_plan.run_plan.items():
                logger.info("Nothing to do. Exiting..")
                return run_plan

            logger.info("Building plan:")
            console.print(Markdown(f"\n\n{run_result_to_markdown(run_plan)}"))

            run_result: RunResult = run_plan
            try:
                steps = Steps(logger=logger, properties=mpyl_run_parameters.run_config.run_properties)
                run_result = run_build(run_plan, steps, reporter)
            except Exception as exc:  # pylint: disable=broad-except
                console.log(f'Exception during build execution: {exc}')
                console.print_exception()
                run_result.exception = exc

            console.print(Markdown(run_result_to_markdown(run_result)))
            return run_result

    except Exception as exc:
        console.log(f'Unexpected exception: {exc}')
        console.print_exception()
        raise exc


def find_build_set(repo: Repository, changes_in_branch, build_all: bool) -> dict[Stage, set[Project]]:
    project_paths = repo.find_projects()
    all_projects = set(map(lambda p: load_project(Path(""), Path(p), False), project_paths))

    if build_all:
        return {Stage.BUILD: for_stage(all_projects, Stage.BUILD),
                Stage.TEST: for_stage(all_projects, Stage.TEST),
                Stage.DEPLOY: for_stage(all_projects, Stage.DEPLOY)}

    return find_invalidated_projects_per_stage(all_projects, changes_in_branch)


def run_build(accumulator: RunResult, executor: Steps, reporter: Optional[Reporter] = None):
    for stage, projects in accumulator.run_plan.items():
        for proj in projects:
            result = executor.execute(stage, proj, True)
            accumulator.append(result)
            if reporter:
                reporter.send_report(accumulator)

            if not result.output.success:
                logging.warning(f'Build failed at {stage} for {proj.name}')
                return accumulator
    return accumulator
