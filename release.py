import asyncio
import time
from typing import Optional

import click
import requests
from requests import Response

from src.mpyl.cli import get_release_url

RELEASE_CHOICES = ["major", "minor", "patch", "rc"]


@click.group()
def cli():
    pass


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
