"""
.. include:: ../../README.md

.. include:: ../../README-usage.md

.. include:: ../../README-dev.md

.. include:: ../../releases/README.md
"""
import logging

import click

from .cli.build import build
from .cli.health import health
from .cli.meta_info import get_version
from .cli.meta_info import version
from .cli.projects import projects
from .cli.repository import repository
from .utilities.pyaml_env import parse_config
from .utilities.repo import RepoConfig, Repository


def _disable_package_loggers(offending_loggers: list[str]):
    for name, _ in logging.root.manager.loggerDict.items():  # pylint: disable=no-member
        for offending_logger in offending_loggers:
            if name.startswith(offending_logger):
                logging.getLogger(name).setLevel(logging.WARNING)


@click.group(name="mpyl", help="Command Line Interface for MPyL")
def main_group():
    """Command Line Interface for MPyL"""


def add_commands():
    main_group.add_command(projects)
    main_group.add_command(build)
    main_group.add_command(version)
    main_group.add_command(health)
    main_group.add_command(repository)


def main():
    _disable_package_loggers(["markdown", "asyncio"])
    add_commands()
    main_group()  # pylint: disable = no-value-for-parameter
