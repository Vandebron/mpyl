import argparse
import logging
import sys
from logging import Logger
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def main(logger: Logger, args: argparse.Namespace):
    if args.local:
        from src.mpyl.project import Project
        from src.mpyl.project import load_project, Stage
        from src.mpyl.reporting.formatting.markdown import run_result_to_markdown
        from src.mpyl.reporting.targets.jira import JiraReporter
        from src.mpyl.stages.discovery import find_invalidated_projects_per_stage
        from src.mpyl.stages.discovery import for_stage
        from src.mpyl.steps.models import RunProperties
        from src.mpyl.steps.run import RunResult
        from src.mpyl.steps.steps import Steps
        from src.mpyl.utilities.pyaml_env import parse_config
        from src.mpyl.utilities.repo import Repository, RepoConfig
    else:
        from mpyl.project import Project
        from mpyl.project import load_project, Stage
        from mpyl.reporting.formatting.markdown import run_result_to_markdown
        from mpyl.reporting.targets.jira import JiraReporter
        from mpyl.stages.discovery import find_invalidated_projects_per_stage
        from mpyl.stages.discovery import for_stage
        from mpyl.steps.models import RunProperties
        from mpyl.steps.run import RunResult
        from mpyl.steps.steps import Steps
        from mpyl.utilities.pyaml_env import parse_config
        from mpyl.utilities.repo import Repository, RepoConfig

    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")

    with Repository(RepoConfig(config)) as repo:
        logger.info(f"Running with {args}")
        if not args.local:
            pull_result = repo.pull_main_branch()
            logger.info(f'Pulled `{pull_result[0].remote_ref_path.strip()}` to local')

        changes_in_branch = repo.changes_in_branch_including_local() if args.local else repo.changes_in_branch()
        logging.debug(f'Changes: {changes_in_branch}')

        project_paths = repo.find_projects()
        logging.info(f" Projects: {len(project_paths)}")

        build_all = args.all

        all_projects = set(map(lambda p: load_project(Path("."), Path(p), False), project_paths))

        projects_per_stage: dict[Stage, set[Project]] = {Stage.BUILD: for_stage(all_projects, Stage.BUILD),
                                                         Stage.TEST: for_stage(all_projects, Stage.TEST),
                                                         Stage.DEPLOY: for_stage(all_projects,
                                                                                 Stage.DEPLOY)} if build_all else \
            find_invalidated_projects_per_stage(all_projects, changes_in_branch)

        for stage, projects in projects_per_stage.items():
            logger.info(f" Stage {stage}: {', '.join(p.name for p in projects)}")

        if args.local:
            properties['build']['versioning']['revision'] = repo.get_sha
            properties['build']['versioning']['pr_number'] = '123'

        run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
        executor = Steps(logger=logger, properties=run_properties)
        logger.info("Building projects")

        run_result = RunResult(run_properties=run_properties, run_plan=projects_per_stage)

        check = None
        slack_channel = None
        slack_personal = None
        jira = None

        if not args.local:
            from mpyl.reporting.targets.github import CommitCheck
            from mpyl.reporting.targets.slack import SlackReporter
            check = CommitCheck(config=config, logger=logger)
            slack_channel = SlackReporter(config, '#project-mpyl', f'MPyL test {run_properties.versioning.identifier}')
            if run_properties.details.user_email:
                slack_personal = SlackReporter(config, None, f'MPyL test {run_properties.versioning.identifier}')
            jira = JiraReporter(config=config, branch=run_properties.versioning.branch or repo.get_branch,
                                logger=logger)
            check.send_report(run_result)

        def __run_build(accumulator: RunResult):
            for stage, projects in projects_per_stage.items():
                for proj in projects:
                    result = executor.execute(stage, proj, args.dryrun)
                    accumulator.append(result)
                    if slack_personal:
                        slack_personal.send_report(accumulator)
                    if not result.output.success:
                        logging.warning(f'Build failed at {stage} for {proj.name}')
                        return accumulator
            return accumulator

        run_result = __run_build(run_result)

        if not args.local:
            check.send_report(run_result)
            slack_channel.send_report(run_result)
            jira.send_report(run_result)

        logging.info(run_result_to_markdown(run_result))
        sys.exit(0 if run_result.is_success else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple MPL pipeline')
    parser.add_argument('--local', '-l', help='a local developer run', default=False, action='store_true')
    parser.add_argument('--all', '-a', help='build and test everything, regardless of the changes that were made',
                        default=False, action='store_true')
    parser.add_argument('--dryrun', '-d', help="don't push or deploy images", default=False, action='store_true')
    parser.add_argument('--verbose', '-v', help="switch to DEBUG level logging", default=False, action='store_true')
    FORMAT = "%(name)s  %(message)s"

    parsed_args = parser.parse_args()
    console = Console(markup=True, width=None if parsed_args.local else 135, no_color=False, log_path=False,
                      color_system='256')
    logging.basicConfig(
        level="DEBUG" if parsed_args.verbose else "INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True,
                              console=console, show_path=parsed_args.local)]
    )
    logger = logging.getLogger("mpl")
    try:
        main(logger, parsed_args)
    except Exception as e:
        logger.warning(f'Unexpected exception: {e}')
        console.print_exception(show_locals=True)
        raise e
