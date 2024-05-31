import logging
import sys
from logging import Logger

from rich.console import Console
from rich.logging import RichHandler

from mpyl.reporting.targets.github import CommitCheck
from mpyl.utilities.pyaml_env import parse_config


def main(logger: Logger):
    config = parse_config("mpyl_config.yml")
    commit_check = CommitCheck(config=config, logger=logger)
    outcome = commit_check.start_check()

    if not outcome.success:
        logger.warning(
            f"Unexpected exception while starting mpyl github commit status check: {outcome.exception}",
            exc_info=True,
        )


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"

    console = Console(
        markup=False,
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
    mpyl_logger.info("Starting mpyl github status check..")
    try:
        main(mpyl_logger)
    except Exception as e:
        mpyl_logger.warning(f"Unexpected exception: {e}", exc_info=True)
        sys.exit(1)
