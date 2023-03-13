"""Simple MPyL build runner"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from ...project import load_project, Stage, Project
from ...reporting.formatting.markdown import run_result_to_markdown
from ...stages.discovery import for_stage, find_invalidated_projects_per_stage
from ...steps.models import RunProperties
from ...steps.run import RunResult
from ...steps.steps import Steps
from ...utilities.repo import Repository, RepoConfig


@dataclass(frozen=True)
class MpylRunConfig:
    config: dict
    run_properties: dict


@dataclass(frozen=True)
class MpylCliParameters:
    local: bool
    verbose: bool = False
    all: bool = False


@dataclass(frozen=True)
class MpylRunParameters:
    config: MpylRunConfig
    parameters: MpylCliParameters


FORMAT = "%(name)s  %(message)s"


def run_mpyl(mpyl_run_parameters: MpylRunParameters):
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
        with Repository(RepoConfig(mpyl_run_parameters.config.config)) as repo:
            logger.info(f"Running with {params}")
            if not params.local:
                pull_result = repo.pull_main_branch()
                logger.info(f'Pulled `{pull_result[0].remote_ref_path.strip()}` to local')

            changes_in_branch = repo.changes_in_branch_including_local() if params.local else repo.changes_in_branch()
            logger.debug(f'Changes: {changes_in_branch}')

            project_paths = repo.find_projects()

            all_projects = set(map(lambda p: load_project(Path("."), Path(p), False), project_paths))

            projects_per_stage: dict[Stage, set[Project]] = find_build_set(all_projects, changes_in_branch, params.all)

            if params.local:
                mpyl_run_parameters.config.run_properties['build']['versioning']['revision'] = repo.get_sha
                mpyl_run_parameters.config.run_properties['build']['versioning']['pr_number'] = '123'

            run_properties = RunProperties.from_configuration(run_properties=mpyl_run_parameters.config.run_properties,
                                                              config=mpyl_run_parameters.config.config)
            logger.info("Building projects")
            run_plan = RunResult(run_properties=run_properties, run_plan=projects_per_stage)
            logger.info(run_result_to_markdown(run_plan))

            run_result = run_build(run_plan, Steps(logger=logger, properties=run_properties))

            logging.info(run_result_to_markdown(run_result))
            sys.exit(0 if run_result.is_success else 1)

    except Exception as exc:
        console.log(f'Unexpected exception: {exc}')
        console.print_exception()
        raise exc


def find_build_set(all_projects, changes_in_branch, build_all: bool) -> dict[Stage, set[Project]]:
    if build_all:
        return {Stage.BUILD: for_stage(all_projects, Stage.BUILD),
                Stage.TEST: for_stage(all_projects, Stage.TEST),
                Stage.DEPLOY: for_stage(all_projects, Stage.DEPLOY)}

    return find_invalidated_projects_per_stage(all_projects, changes_in_branch)


def run_build(accumulator: RunResult, executor: Steps):
    for stage, projects in accumulator.run_plan.items():
        for proj in projects:
            result = executor.execute(stage, proj, True)
            accumulator.append(result)
            if not result.output.success:
                logging.warning(f'Build failed at {stage} for {proj.name}')
                return accumulator
    return accumulator
