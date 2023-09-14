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


def switch_to_main(git):
    current_branch = git.rev_parse("HEAD", abbrev_ref=True)
    if current_branch != "main":
        if questionary.confirm(
            f"Current branch: {current_branch}. Must be on main. Switch?"
        ).ask():
            git.checkout("main")
        else:
            click.echo("Aborting")
            sys.exit()


@click.group()
def cli():
    pass


@cli.command(help="Publish the latest release")
def publish():
    git = Git()
    switch_to_main(git)
    latest: Release = get_latest_release()
    should_publish = questionary.confirm(f"Publish release {latest}").ask()
    if should_publish:
        prerelease = "--prerelease" if latest.release_candidate else ""
        output = custom_check_output(
            logging.getLogger(),
            f"gh release create {latest} --generate-notes {prerelease}",
        )
        if output.success:
            click.echo("Release published")
        else:
            click.echo("Release not published")
            click.echo(output.message)
            sys.exit(1)


@cli.command(help="Create a new release")
@click.option("--level", "-l", type=click.Choice(RELEASE_CHOICES))
def create(level: Optional[str]):
    git = Git()
    switch_to_main(git)
    if git.is_dirty():
        click.echo("Main branch is dirty, aborting")
        sys.exit()

    latest: Release = get_latest_release()
    if level is None:
        level = questionary.select(
            f"Latest release is {latest}. What type of release do you want to create?",
            choices=RELEASE_CHOICES,
            instruction="Versions are identified by 'major.minor.patch(rcN)+'",
        ).ask()

    releases = {
        "major": Release(latest.major + 1, 0, 0, None),
        "minor": Release(latest.major, latest.minor + 1, 0, None),
        "patch": Release(latest.major, latest.minor, latest.patch + 1, None),
        "rc": Release(
            latest.major, latest.minor, latest.patch, latest.release_candidate or 0 + 1
        ),
    }
    new_version = releases[level]

    confirmed = questionary.confirm(f"Create {level} release {new_version}").ask()
    if confirmed:
        git.checkout("-b", f"release/{new_version}")
        add_release(new_version)
        if level != "rc":
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
        output = custom_check_output(logging.getLogger(), "gh pr create -f")
        if output.success:
            click.echo("PR created. After merge, run `mpyl release publish`")


@cli.command(help="Check if a release exists on the pypi registry")
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
