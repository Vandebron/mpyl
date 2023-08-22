"""Health check command"""

import click

from . import create_console_logger
from .commands.health.checks import perform_health_checks


@click.command("health")
@click.option(
    "--ci",
    "is_ci",
    is_flag=True,
    default=False,
    help="Run health checks relevant only for CI builds.",
)
def health(is_ci):
    """Health check"""
    console = create_console_logger(show_path=False, verbose=False, max_width=0)
    perform_health_checks(console, is_ci)
