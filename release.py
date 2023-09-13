import asyncio
import logging
import sys
import time
from typing import Optional

import click
import questionary

from src.mpyl.projects.versioning import Release, get_latest_release
from src.mpyl.steps import Output
from src.mpyl.utilities.subprocess import custom_check_output

RELEASE_CHOICES = ["major", "minor", "patch", "rc"]


@click.group()
def cli():
    pass


@cli.command()
@click.option("--level", "-l", type=click.Choice(RELEASE_CHOICES))
def create(level: Optional[str]):
    latest: Release = get_latest_release()
    if not level:
        level = questionary.select(
            f"Latest release is {latest}. What type of release do you want to create?",
            choices=RELEASE_CHOICES,
            instruction="Versions are identified by 'major.minor.patch(rcN)+'",
        ).ask()
    new_version = Release(
        latest.major + (1 if level == "major" else 0),
        latest.minor + (1 if level == "minor" else 0),
        latest.patch + (1 if level == "patch" else 0),
        (1 if latest.release_candidate is None else latest.release_candidate + 1)
        if level == "rc"
        else None,
    )
    confirmed = questionary.confirm(f"Create {level} release {new_version}").ask()
    print(f"Confirmed: {confirmed}")


@cli.command()
@click.argument("version")
@click.option("--test", "-t", type=click.BOOL, default=False, is_flag=True)
@click.option("--attempts", "-a", type=click.INT, default=1, is_flag=False)
def exists(version, test, attempts):
    try:
        attempt = 0
        output: Optional[Output] = None
        while attempt < attempts:
            url = f"https://{'test.' if test else ''}pypi.org/simple/"
            output: Output = custom_check_output(
                logging.getLogger(),
                f"pip install --dry-run -i {url} mpyl=={version}",
                capture_stdout=False,
            )
            if output.success:
                click.echo(f"Release {version} discovered")
                sys.exit(0)

            attempt += 1
            click.echo(f"Attempt {attempt} out of {attempts}")
            time.sleep(2)

        click.echo(f"Release {version} not found")
        click.echo(output.message)
        sys.exit(1)
    except asyncio.TimeoutError:
        click.echo("Gave up waiting, task canceled")


if __name__ == "__main__":
    cli()
