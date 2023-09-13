import asyncio
import time

import click

from src.mpyl.cli import does_publication_exist

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
            check_exists = asyncio.wait_for(
                does_publication_exist(version, test), timeout=10
            )
            release_exists = asyncio.get_event_loop().run_until_complete(check_exists)
            if release_exists:
                click.echo(f"Release {version} discovered")
                break
            attempt += 1
            click.echo(
                f"Release {version} not found. Attempt {attempt} out of {attempts}"
            )
            time.sleep(2)
    except asyncio.TimeoutError:
        click.echo("Gave up waiting, task canceled")


if __name__ == "__main__":
    cli()
