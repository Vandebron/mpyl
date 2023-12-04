import logging
import pickle
import sys
from logging import Logger
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from mpyl.constants import BUILD_ARTIFACTS_FOLDER
from mpyl.reporting.targets.github import CommitCheck
from mpyl.reporting.targets.slack import SlackReporter
from mpyl.steps.run import RunResult
from mpyl.reporting.targets import ReportAccumulator
from mpyl.reporting.targets.github import PullRequestReporter
from mpyl.reporting.targets.jira import compose_build_status
from mpyl.reporting.targets.jira import JiraReporter
from mpyl.steps.models import RunProperties
from mpyl.utilities.pyaml_env import parse_config


def main(logger: Logger):
    run_result_file = Path(BUILD_ARTIFACTS_FOLDER) / "run_result"

    if not run_result_file.is_file():
        logger.info(f"Run result file {run_result_file} not found. Nothing to report.")
        sys.exit()

    with open(run_result_file, "rb") as file:
        run_result: RunResult = pickle.load(file)

        accumulator = ReportAccumulator()
        config = parse_config("mpyl_config.yml")
        properties = parse_config("run_properties.yml")
        run_properties = RunProperties.from_configuration(
            run_properties=properties, config=config
        )

        commit_check = CommitCheck(config=config, logger=logger)
        accumulator.add(commit_check.send_report(run_result))

        slack_channel = SlackReporter(
            config=config,
            channel="#project-mpyl-notifications",
            versioning_identifier=run_properties.versioning.identifier,
            target=run_properties.target,
        )
        accumulator.add(slack_channel.send_report(run_result))

        if run_properties.details.user_email:
            slack_personal = SlackReporter(
                config=config,
                channel=None,
                versioning_identifier=run_properties.versioning.identifier,
                target=run_properties.target,
            )
            slack_personal.send_report(run_result)

        jira = JiraReporter(
            config=config, branch=run_properties.versioning.branch, logger=logger
        )
        accumulator.add(jira.send_report(run_result))

        github_comment = PullRequestReporter(
            config=config,
            compose_function=compose_build_status,
        )
        accumulator.add(github_comment.send_report(run_result))

        if accumulator.failures:
            logger.warning(
                f'Failed to send the following report(s): {", ".join(accumulator.failures)}'
            )


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"

    console = Console(
        markup=False,
        width=200,
        no_color=False,
        log_path=False,
        color_system="256",
    )
    logging.raiseExceptions = False
    logging.basicConfig(
        level="INFO",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(markup=False, console=console, show_path=False)],
    )

    mpyl_logger = logging.getLogger("mpyl")
    mpyl_logger.info("Starting reporting...")
    try:
        main(mpyl_logger)
    except Exception as e:
        mpyl_logger.warning(f"Unexpected exception: {e}", exc_info=True)
        sys.exit(1)
