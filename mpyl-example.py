import argparse
import logging
import sys
from logging import Logger


def main(log: Logger, args: argparse.Namespace):
    # if args.local:
    from src.mpyl.reporting.targets.jira import JiraReporter
    from src.mpyl.steps.models import RunProperties
    from src.mpyl.utilities.pyaml_env import parse_config
    from src.mpyl.cli import MpylCliParameters
    from src.mpyl.build import run_mpyl

    # else:
    #     from mpyl.reporting.targets.jira import JiraReporter
    #     from mpyl.steps.models import RunProperties
    #     from mpyl.utilities.pyaml_env import parse_config
    #     from mpyl.build import run_mpyl
    #     from mpyl.cli import MpylCliParameters

    config = parse_config("mpyl_config.yml")
    properties = parse_config("run_properties.yml")
    run_properties = RunProperties.from_configuration(
        run_properties=properties, config=config, cli_tag=args.tag
    )
    check = None
    slack_channel = None
    slack_personal = None
    jira = None
    github_comment = None

    if not args.local:
        from mpyl.reporting.targets.github import CommitCheck
        from mpyl.reporting.targets.slack import SlackReporter
        from mpyl.steps.run import RunResult
        from mpyl.reporting.targets.github import PullRequestReporter
        from mpyl.reporting.targets.jira import compose_build_status
        from mpyl.reporting.targets import ReportAccumulator

        check = CommitCheck(config=config, logger=log)
        accumulator = ReportAccumulator()

        github_comment = PullRequestReporter(
            config=config,
            compose_function=compose_build_status,
        )
        slack_channel = SlackReporter(
            config=config,
            channel="#project-mpyl-notifications",
            versioning_identifier=run_properties.versioning.identifier,
            target=run_properties.target,
        )

        if run_properties.details.user_email:
            slack_personal = SlackReporter(
                config=config,
                channel=None,
                versioning_identifier=run_properties.versioning.identifier,
                target=run_properties.target,
            )

        jira = JiraReporter(
            config=config, branch=run_properties.versioning.branch, logger=log
        )
        accumulator.add(
            check.send_report(RunResult(run_properties=run_properties, run_plan={}))
        )

    cli_parameters = MpylCliParameters(
        local=args.local,
        tag=args.tag,
        pull_main=True,
        verbose=args.verbose,
        all=args.all,
        dryrun=args.dryrun,
        version=args.version,
    )
    run_result = run_mpyl(
        run_properties=run_properties,
        cli_parameters=cli_parameters,
        reporter=slack_personal,
    )

    if not args.local:
        accumulator.add(check.send_report(run_result))
        accumulator.add(slack_channel.send_report(run_result))
        if slack_personal:
            slack_personal.send_report(run_result)
        accumulator.add(jira.send_report(run_result))
        accumulator.add(github_comment.send_report(run_result))
        if accumulator.failures:
            log.warning(
                f'Failed to send the following report(s): {", ".join(accumulator.failures)}'
            )
            sys.exit(1)

    sys.exit(0 if run_result.is_success else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple MPL pipeline")
    parser.add_argument(
        "--local",
        "-l",
        help="a local developer run",
        default=False,
        action="store_true",
    )
    parser.add_argument("--tag", "-t", help="The name of the tag to build", type=str)
    parser.add_argument(
        "--all",
        "-a",
        help="build and test everything, regardless of the changes that were made",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--dryrun",
        "-d",
        help="don't push or deploy images",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        help="switch to DEBUG level logging",
        default=False,
        action="store_true",
    )
    FORMAT = "%(name)s  %(message)s"

    parsed_args = parser.parse_args()
    mpl_logger = logging.getLogger("mpyl")
    mpl_logger.info("Starting run.....")
    try:
        main(mpl_logger, parsed_args)
    except Exception as e:
        mpl_logger.warning(f"Unexpected exception: {e}", exc_info=True)
        sys.exit(1)
