import logging
import pickle
import sys
from logging import Logger
from pathlib import Path

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
    config = parse_config("mpyl_config.yml")
    properties = parse_config("run_properties.yml")
    run_properties = RunProperties.from_configuration(
        run_properties=properties, config=config
    )
    slack_personal = None

    check = CommitCheck(config=config, logger=logger)
    accumulator = ReportAccumulator()
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
        config=config, branch=run_properties.versioning.branch, logger=logger
    )

    run_result_file = Path(BUILD_ARTIFACTS_FOLDER) / "run_result"

    if not run_result_file.is_file():
        logger.info(f"Run result file {run_result_file} not found. Nothing to report.")
        sys.exit()

    with open(run_result_file, "rb") as file:
        run_result: RunResult = pickle.load(file)
        accumulator.add(check.send_report(run_result))
        accumulator.add(slack_channel.send_report(run_result))
        if slack_personal:
            slack_personal.send_report(run_result)
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

    mpl_logger = logging.getLogger("mpyl")
    mpl_logger.info("Starting reporting.....")
    try:
        main(mpl_logger)
    except Exception as e:
        mpl_logger.warning(f"Unexpected exception: {e}", exc_info=True)
        sys.exit(1)
