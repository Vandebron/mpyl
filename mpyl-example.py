import logging
from logging import Logger

from pyaml_env import parse_config
from rich.console import Console
from rich.logging import RichHandler

from src.mpyl.project import load_project, Stage
from src.mpyl.reporting.markdown import run_result_to_markdown
from src.mpyl.utilities.repo import Repository, RepoConfig, History
from src.mpyl.reporting.simple import to_string
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.steps.models import RunProperties
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps


def main(repo: Repository, log: Logger, dry_run: bool):
    changes_in_branch: list[History] = repo.changes_in_branch()
    project_paths = repo.find_projects()
    logging.info(f" Projects: {len(project_paths)}")

    log.info(f" Build stage: {len(find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch))}")
    log.info(f" Test stage: {len(find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch))}")
    log.info(f" Deploy stage: {len(find_invalidated_projects_for_stage(repo, Stage.DEPLOY, changes_in_branch))}")
    log.info(
        f" Post deploy stage: {len(find_invalidated_projects_for_stage(repo, Stage.POST_DEPLOY, changes_in_branch))}")
    all_projects = list(map(lambda p: load_project(".", p, False), project_paths))

    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")
    properties['build']['versioning']['revision'] = repo.get_sha
    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    executor = Steps(logger=log, properties=run_properties)
    log.info(" Building projects")

    run_result = RunResult(run_properties)

    for proj in find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch):
        run_result.append(executor.execute(Stage.BUILD, proj, dry_run))
    for proj in find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch):
        run_result.append(executor.execute(Stage.TEST, proj, dry_run))
    for proj in find_invalidated_projects_for_stage(repo, Stage.DEPLOY, changes_in_branch):
        run_result.append(executor.execute(Stage.DEPLOY, proj, dry_run))

    log.info(run_result_to_markdown(run_result), extra={"markup": True})


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True, console=Console(markup=True), show_path=True)]
    )

    yaml_values = parse_config("config.yml")

    logger = logging.getLogger("mpl")
    repo = Repository(RepoConfig(yaml_values))
    pull_result = repo.pull_main_branch()
    logger.info(pull_result[0].remote_ref_path)
    project_paths = repo.find_projects()
    logger.info(project_paths)

    main(repo, logger, dry_run=True)
