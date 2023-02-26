import argparse
import logging
from argparse import Namespace
from logging import Logger

from pyaml_env import parse_config
from rich.console import Console
from rich.logging import RichHandler

from src.mpyl.project import load_project, Stage
from src.mpyl.reporting.markdown import run_result_to_markdown
from src.mpyl.utilities.repo import Repository, RepoConfig, History
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.steps.models import RunProperties
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps


def main(repo: Repository, log: Logger, args: Namespace):
    changes_in_branch: list[History] = repo.changes_in_branch()
    project_paths = repo.find_projects()
    logging.info(f" Projects: {len(project_paths)}")

    all = args.all

    all_projects = list(map(lambda p: load_project(".", p, False), project_paths))

    build_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch)
    test_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch)
    deploy_projects = all_projects if all else find_invalidated_projects_for_stage(repo, Stage.DEPLOY,
                                                                                   changes_in_branch)

    log.info(f" Build stage: {len(build_projects)}")
    log.info(f" Test stage: {len(test_projects)}")
    log.info(f" Deploy stage: {len(deploy_projects)}")
    log.info(
        f" Post deploy stage: {len(find_invalidated_projects_for_stage(repo, Stage.POST_DEPLOY, changes_in_branch))}")

    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")
    if args.local:
        properties['build']['versioning']['revision'] = repo.get_sha

    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    executor = Steps(logger=log, properties=run_properties)
    log.info(" Building projects")

    run_result = RunResult(run_properties)

    for proj in build_projects:
        run_result.append(executor.execute(Stage.BUILD, proj, dry_run=args.dryrun))
    for proj in test_projects:
        run_result.append(executor.execute(Stage.TEST, proj, dry_run=args.dryrun))
    for proj in deploy_projects:
        run_result.append(executor.execute(Stage.DEPLOY, proj, dry_run=args.dryrun))

    log.info(run_result_to_markdown(run_result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple MPL pipeline')
    parser.add_argument('--local', '-l', help='a local developer run', default=False, action='store_true')
    parser.add_argument('--all', '-a', help='build and test everything, regardless of the changes that were made',
                        default=False, action='store_true')
    parser.add_argument('--dryrun', '-d', help="don't push or deploy images", default=False, action='store_true')
    args: Namespace = parser.parse_args()

    FORMAT = "%(name)s  %(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]",
        handlers=[
            RichHandler(markup=True, console=Console(markup=True, width=None if args.local else 135, no_color=False,
                                                     color_system='256'), show_path=True)]
    )

    yaml_values = parse_config("config.yml")

    logger = logging.getLogger("mpl")
    repository = Repository(RepoConfig(yaml_values))

    if not args.local:
        pull_result = repository.pull_main_branch()
        logger.info(f'Pulled {pull_result[0].remote_ref_path} to local')

    main(repository, logger, args)
