"""
.. include:: ../../README.md

.. include:: ../../README-usage.md

.. include:: ../../README-dev.md
"""

import click

from .cli.build import build
from .cli.health import health
from .cli.meta_info import get_version
from .cli.meta_info import version
from .cli.projects import projects
from .utilities.pyaml_env import parse_config
from .utilities.repo import RepoConfig, Repository


@click.group(name='mpyl')
def main_group():
    """Command Line Interface for MPyL"""


def main():
    main_group.help = f"Command Line Interface for MPyL {get_version()}"
    main_group.add_command(projects)
    main_group.add_command(build)
    main_group.add_command(version)
    main_group.add_command(health)
    main_group()  # pylint: disable = no-value-for-parameter
