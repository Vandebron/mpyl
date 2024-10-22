import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler


def main(args: argparse.Namespace):
    if args.local:
        from src.mpyl.steps.run_properties import construct_run_properties
        from src.mpyl.utilities.pyaml_env import parse_config
        from src.mpyl.cli import MpylCliParameters
        from src.mpyl.build import run_mpyl
        from plugins.gradle import BuildGradle

    else:
        from mpyl.steps.run_properties import construct_run_properties
        from mpyl.utilities.pyaml_env import parse_config
        from mpyl.build import run_mpyl
        from mpyl.cli import MpylCliParameters

    config = parse_config("mpyl_config.yml")
    properties = parse_config("run_properties.yml")
    cli_parameters = MpylCliParameters(
        local=args.local,
        tag=args.tag,
        pull_main=True,
        verbose=args.verbose,
        all=args.all,
        dryrun=args.dryrun,
    )
    run_properties = construct_run_properties(
        config=config, properties=properties, cli_parameters=cli_parameters
    )

    run_result = run_mpyl(
        run_properties=run_properties,
        cli_parameters=cli_parameters,
        reporter=None,
    )

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
    console = Console(
        markup=False,
        width=None if parsed_args.local else 200,
        no_color=False,
        log_path=False,
        color_system="256",
    )
    logging.raiseExceptions = False
    logging.basicConfig(
        level="DEBUG" if parsed_args.verbose else "INFO",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[
            RichHandler(markup=False, console=console, show_path=parsed_args.local)
        ],
    )

    mpyl_logger = logging.getLogger("mpyl")
    mpyl_logger.info("Starting run...")
    try:
        main(parsed_args)
    except Exception as e:
        mpyl_logger.warning(f"Unexpected exception: {e}", exc_info=True)
        sys.exit(1)
