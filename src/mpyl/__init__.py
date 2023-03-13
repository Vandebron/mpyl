"""
.. include:: ../../README.md

.. include:: ../../README-usage.md

.. include:: ../../README-dev.md
"""

from importlib.metadata import version as version_meta

import click

from .cli.commands.build import build
from .cli.commands.meta_info import version
from .cli.commands.projects import projects
from .utilities.pyaml_env import parse_config
from .utilities.repo import RepoConfig, Repository


@click.group(name='mpyl', help=f"Command Line Interface for MPyL {version_meta('mpyl')}")
def main_group():
    """Command Line Interface for MPyL"""


def main():
    main_group.add_command(projects)
    main_group.add_command(build)
    main_group.add_command(version)
    main_group()  # pylint: disable = no-value-for-parameter
