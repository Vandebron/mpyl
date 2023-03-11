"""
.. include:: ../../README.md

.. include:: ../../README-usage.md

.. include:: ../../README-dev.md
"""

import click

from .cli.meta_info import MetaInfo


@click.command()
@click.option('--version', help='Shows MPyL version', is_flag=True)
@click.option('--about', help='Shows legal info and metadata', is_flag=True)
def main(version, about):
    """Command Line Interface for MPyL"""
    if version:
        MetaInfo().print_version()
    if about:
        MetaInfo().print_about()


if __name__ == '__main__':
    main()  # pylint: disable = no-value-for-parameter
