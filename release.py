import asyncio
import logging
import sys
import time
from typing import Optional

import click
import questionary
import requests
from git import Git
from requests import Response

from src.mpyl.cli import get_release_url
from src.mpyl.projects.versioning import (
    Release,
    get_latest_release,
    add_release,
    render_release_notes,
    get_release_notes_readme_path,
    get_release_notes_path,
)
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
            f"gh release create {latest} --generate-notes {prerelease}".strip(),
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
    if git.status("--short") != "":
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
        "minor": Release(
            latest.major, latest.minor + (0 if latest.release_candidate else 1), 0, None
        ),
        "patch": Release(latest.major, latest.minor, latest.patch + 1, None),
        "rc": Release(
            latest.major,
            latest.minor + (1 if latest.release_candidate is None else 0),
            latest.patch if latest.release_candidate is not None else 0,
            (latest.release_candidate or 0) + 1,
        ),
    }
    new_version = releases[level]

    confirmed = questionary.confirm(f"Create {level} release {new_version}").ask()
    if confirmed:
        branch_name = f"release/{new_version}"
        git.checkout("-b", branch_name)
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

        click.echo("Creating release notes...")
        get_release_notes_readme_path().write_text(
            render_release_notes(), encoding="utf-8"
        )
        git.add(".")
        git.commit("-m", f"Release {new_version}")
        git.push("--set-upstream", "origin", branch_name)
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
        while attempt < attempts:
            check_exists = asyncio.wait_for(get_release_url(version, test), timeout=10)
            maybe_release_url = asyncio.get_event_loop().run_until_complete(
                check_exists
            )
            response: Optional[Response] = None

            if maybe_release_url:
                click.echo(f"Release {version} discovered")
                response = requests.get(maybe_release_url, timeout=10)
                if response.status_code == 200:
                    click.echo(
                        f"Binary for {version} is present at {maybe_release_url}"
                    )
                    sys.exit()

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

        click.echo(f"Release {version} not found")
        sys.exit(1)
    except asyncio.TimeoutError:
        click.echo("Gave up waiting, task canceled")


if __name__ == "__main__":
    cli()
