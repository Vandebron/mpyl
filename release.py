import asyncio
import logging
import sys
import time
from typing import Optional

import click
import questionary
from git import Git

from src.mpyl.projects.versioning import (
    Release,
    get_latest_release,
    add_release,
    render_release_notes,
    get_release_notes_readme_path,
    get_release_notes_path,
)
from src.mpyl.steps import Output
from src.mpyl.utilities.subprocess import custom_check_output

RELEASE_CHOICES = ["major", "minor", "patch", "rc"]


@click.group()
def cli():
    pass


@cli.command()
@click.option("--level", "-l", type=click.Choice(RELEASE_CHOICES))
def create(level: Optional[str]):
    git = Git()
    current_branch = git.rev_parse("HEAD", abbrev_ref=True)
    if (
        current_branch != "main"
        and not questionary.confirm(
            f"Current branch: {current_branch}. Must be on main. Switch?"
        ).ask()
    ):
        git.checkout("main")
        if git.is_dirty():
            click.echo("Main branch is dirty, aborting")
            sys.exit()

    latest: Release = get_latest_release()
    if not level:
        level = questionary.select(
            f"Latest release is {latest}. What type of release do you want to create?",
            choices=RELEASE_CHOICES,
            instruction="Versions are identified by 'major.minor.patch(rcN)+'",
        ).ask()
    new_version = Release(
        latest.major + 1 if level == "major" else latest.major,
        latest.minor + 1
        if level == "minor" or level == "rc"
        else (latest.minor if level == "patch" else 0),
        latest.patch + 1 if level == "patch" else 0,
        (1 if latest.release_candidate is None else latest.release_candidate + 1)
        if level == "rc"
        else None,
    )
    confirmed = questionary.confirm(f"Create {level} release {new_version}").ask()
    if confirmed:
        git.checkout("-b", f"release/{new_version}")
        add_release(new_version)
        if level is not "rc":
            release_notes = get_release_notes_path(new_version)
            if (
                not release_notes.exists()
                and questionary.confirm(
                    f"Create notes for {new_version} at {str(release_notes)}"
                ).ask()
            ):
                release_notes.write_text(f"### TODO: Release notes for {new_version}")
                sys.exit()

        get_release_notes_readme_path().write_text(
            render_release_notes(), encoding="utf-8"
        )
        git.add(".")
        git.commit("-m", f"Release {new_version}")
        output: Output = custom_check_output(logging.getLogger(), "gh pr create -f")
        if output.success:
            click.echo("PR created. After merge, run `mpyl release publish`")


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
