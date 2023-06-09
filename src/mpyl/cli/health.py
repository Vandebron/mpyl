"""Health check command"""

import click

from . import create_console_logger
from .commands.health.checks import perform_health_checks


@click.command('health')
def health():
    """Health check"""
    console = create_console_logger(local=False, verbose=False)
    perform_health_checks(console)
