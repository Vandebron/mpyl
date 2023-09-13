import asyncio
import time
from typing import Optional

import click
import questionary
import requests
from requests import Response

from src.mpyl.projects.versioning import Release, get_latest_release
from src.mpyl.cli import get_release_url

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
        while attempt < attempts:
            check_exists = asyncio.wait_for(get_release_url(version, test), timeout=10)
            maybe_release_url = asyncio.get_event_loop().run_until_complete(
                check_exists
            )
            response: Optional[Response] = None
            if maybe_release_url:
                response = requests.get(maybe_release_url, timeout=10)
                if response.status_code == 200:
                    click.echo(f"Release {version} discovered")
                    break

            attempt += 1
            attempt_text = f"Attempt {attempt} out of {attempts}"
            if response:
                click.echo(
                    f"Release {version} found, but binary gives {response.status_code}. {attempt_text}"
                )
            else:
                click.echo(
                    f"Release {version} not found. Attempt {attempt} out of {attempts}"
                )
            time.sleep(2)
    except asyncio.TimeoutError:
        click.echo("Gave up waiting, task canceled")


if __name__ == "__main__":
    cli()
