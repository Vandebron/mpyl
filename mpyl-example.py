import argparse
import logging
import sys
from logging import Logger

from pyaml_env import parse_config
from rich.console import Console
from rich.logging import RichHandler

from src.mpyl.stages.discovery import for_stage


def main(log: Logger, args: argparse.Namespace):
    if args.local:
        from src.mpyl.project import load_project, Stage
        from src.mpyl.reporting.formatting.markdown import run_result_to_markdown
        from src.mpyl.stages.discovery import find_invalidated_projects_per_stage
        from src.mpyl.steps.models import RunProperties
        from src.mpyl.steps.run import RunResult
        from src.mpyl.steps.steps import Steps
        from src.mpyl.utilities.repo import Repository, RepoConfig, History
    else:
        from mpyl.project import load_project, Stage
        from mpyl.reporting.formatting.markdown import run_result_to_markdown
        from mpyl.stages.discovery import find_invalidated_projects_per_stage
        from mpyl.steps.models import RunProperties
        from mpyl.steps.run import RunResult
        from mpyl.steps.steps import Steps
        from mpyl.utilities.repo import Repository, RepoConfig, History

    repo = Repository(RepoConfig(parse_config("config.yml")))
    log.info(f"Running with {args}")
    if not args.local:
        pull_result = repo.pull_main_branch()
        log.info(f'Pulled `{pull_result[0].remote_ref_path.strip()}` to local')

    changes_in_branch: list[History] = repo.changes_in_branch()
    logging.debug(f'Changes: {changes_in_branch}')

    project_paths = repo.find_projects()
    logging.info(f" Projects: {len(project_paths)}")

    build_all = args.all

    all_projects = set(map(lambda p: load_project(".", p, False), project_paths))

    projects_per_stage = {Stage.BUILD: for_stage(all_projects, Stage.BUILD),
                          Stage.TEST: for_stage(all_projects, Stage.TEST),
                          Stage.DEPLOY: for_stage(all_projects, Stage.DEPLOY)} if build_all else \
        find_invalidated_projects_per_stage(all_projects, changes_in_branch)

    for stage, projects in projects_per_stage.items():
        log.info(f" Stage {stage}: {', '.join(p.name for p in projects)}")

    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")
    if args.local:
        properties['build']['versioning']['revision'] = repo.get_sha
        properties['build']['versioning']['pr_number'] = '123'

    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    executor = Steps(logger=log, properties=run_properties)
    log.info("Building projects")

    run_result = RunResult(run_properties)

    check = None
    slack = None

    if not args.local:
        from mpyl.reporting.targets.github import CommitCheck
        from mpyl.reporting.targets.slack import SlackReporter
        check = CommitCheck(config=config)
        slack = SlackReporter(config, '#project-mpyl', 'MPyL test build')
        check.send_report(run_result)

    def __run_build(accumulator: RunResult):
        for stage, projects in projects_per_stage.items():
            for proj in projects:
                result = executor.execute(stage, proj, args.dryrun)
                accumulator.append(result)
                if not result.output.success:
                    logging.warning(f'Build failed at {stage} for {proj.name}')
                    return accumulator
        return accumulator

    run_result = __run_build(run_result)

    if not args.local:
        check.send_report(run_result)
        slack.send_report(run_result)

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
    logging.basicConfig(
        level="DEBUG" if parsed_args.verbose else "INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True,
                              console=Console(markup=True, width=None if parsed_args.local else 135, no_color=False,
                                              log_path=False, color_system='256'), show_path=parsed_args.local)]
    )

    main(logging.getLogger("mpl"), parsed_args)
