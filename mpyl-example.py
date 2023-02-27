import argparse
import logging
from logging import Logger

from pyaml_env import parse_config
from rich.console import Console
from rich.logging import RichHandler

from src.mpyl.project import load_project, Stage
from src.mpyl.reporting.markdown import run_result_to_markdown
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.steps.models import RunProperties
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps
from src.mpyl.utilities.repo import Repository, RepoConfig, History


def main(repo: Repository, log: Logger, args: argparse.Namespace):
    if not args.local:
        pull_result = repo.pull_main_branch()
        log.info(f'Pulled `{pull_result[0].remote_ref_path}` to local')

    changes_in_branch: list[History] = repo.changes_in_branch()
    project_paths = repo.find_projects()
    logging.info(f" Projects: {len(project_paths)}")

    all = args.all

    all_projects = set(map(lambda p: load_project(".", p, False), project_paths))

    build_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch)
    test_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch)
    deploy_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.DEPLOY,
                                                                                   changes_in_branch)

    log.info(f" Build stage: {', '.join(p.name for p in build_projects)}")
    log.info(f" Test stage: {', '.join(p.name for p in test_projects)}")
    log.info(f" Deploy stage: {', '.join(p.name for p in deploy_projects)}")

    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")
    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    executor = Steps(logger=log, properties=run_properties)
    log.info(" Building projects")

    run_result = RunResult(run_properties)

    for proj in build_projects:
        run_result.append(executor.execute(Stage.BUILD, proj, args.dryrun))
    for proj in test_projects:
        run_result.append(executor.execute(Stage.TEST, proj, args.dryrun))
    for proj in deploy_projects:
        run_result.append(executor.execute(Stage.DEPLOY, proj, args.dryrun))

    logging.info(run_result_to_markdown(run_result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple MPL pipeline')
    parser.add_argument('--local', '-l', help='a local developer run', default=False, action='store_true')
    parser.add_argument('--all', '-a', help='build and test everything, regardless of the changes that were made',
                        default=False, action='store_true')
    parser.add_argument('--dryrun', '-d', help="don't push or deploy images", default=False, action='store_true')
    FORMAT = "%(name)s  %(message)s"

    parsed_args = parser.parse_args()
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True,
                              console=Console(markup=True, width=None if parsed_args.local else 135, no_color=False,
                                              log_path=False, color_system='256'), show_path=parsed_args.local)]
    )

    yaml_values = parse_config("config.yml")
    main(Repository(RepoConfig(yaml_values)), logging.getLogger("mpl"), parsed_args)
