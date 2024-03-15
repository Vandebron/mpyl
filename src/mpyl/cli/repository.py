"""Commands related to the VCS (git) repository"""
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console

from . import (
    CONFIG_PATH_HELP,
    create_console_logger,
)
from ..constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME


@dataclass(frozen=True)
class RepoContext:
    config: Path
    run_properties: Path
    console: Console
    verbose: bool


@click.group("repo")
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=False),
    help=CONFIG_PATH_HELP,
    envvar="MPYL_CONFIG_PATH",
    default=DEFAULT_CONFIG_FILE_NAME,
)
@click.option(
    "--properties",
    "-p",
    required=False,
    type=click.Path(exists=False),
    help="Path to run properties",
    envvar="MPYL_RUN_PROPERTIES_PATH",
    default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
    show_default=True,
)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.pass_context
def repository(ctx, config, properties, verbose):
    """Manage CVS (git) repositories"""
    console = create_console_logger(show_path=False, verbose=verbose)
    ctx.obj = RepoContext(
        config=config, run_properties=properties, console=console, verbose=verbose
    )
