import logging
from logging import Logger

from pyaml_env import parse_config
from rich.console import Console
from rich.logging import RichHandler

from src.mpyl.project import load_project, Stage
from src.mpyl.utilities.repo import Repository, RepoConfig, History
from src.mpyl.reporting.simple import to_string
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.steps.models import RunProperties
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps


def main(repo: Repository, log: Logger):
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
    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    executor = Steps(logger=log, properties=run_properties)
    log.info(" Building projects")

    run_result = RunResult(run_properties)

    for proj in find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch):
        run_result.append(executor.execute(Stage.BUILD, proj))
    for proj in find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch):
        run_result.append(executor.execute(Stage.TEST, proj))
    for proj in find_invalidated_projects_for_stage(repo, Stage.DEPLOY, changes_in_branch):
        run_result.append(executor.execute(Stage.DEPLOY, proj))

    print(to_string(run_result))


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True, console=Console(width=255), show_path=True)]
    )

    yaml_values = parse_config("config.yml")
    main(Repository(RepoConfig(yaml_values)), logging.getLogger("mpl"))
