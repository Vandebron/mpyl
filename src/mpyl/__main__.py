"""Entrypoint for cli"""

import click

from .cli.build import build
from .cli.meta_info import version
from .cli.projects import projects


@click.group(name='mpyl')
def main():
    """Command Line Interface for MPyL"""


if __name__ == '__main__':
    main.add_command(projects)
    main.add_command(build)
    main.add_command(version)
    main()  # pylint: disable = no-value-for-parameter
