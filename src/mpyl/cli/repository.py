"""Commands related to the VCS (git) repository"""
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown

from . import (
    CONFIG_PATH_HELP,
    create_console_logger,
)
from ..constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from ..steps.models import RunProperties
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


@dataclass(frozen=True)
class RepoContext:
    config: Path
    run_properties: Path
    console: Console
    verbose: bool


@click.group("repo")
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=False),
    help=CONFIG_PATH_HELP,
    envvar="MPYL_CONFIG_PATH",
    default=DEFAULT_CONFIG_FILE_NAME,
)
@click.option(
    "--properties",
    "-p",
    required=False,
    type=click.Path(exists=False),
    help="Path to run properties",
    envvar="MPYL_RUN_PROPERTIES_PATH",
    default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
    show_default=True,
)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.pass_context
def repository(ctx, config, properties, verbose):
    """Manage CVS (git) repositories"""
    console = create_console_logger(show_path=False, verbose=verbose)
    ctx.obj = RepoContext(
        config=config, run_properties=properties, console=console, verbose=verbose
    )


@repository.command(help="The status of the current local repository")
@click.pass_obj
def status(obj: RepoContext):
    """Print the status of the current repository"""
    config = parse_config(obj.config)
    run_properties = RunProperties.from_configuration(
        parse_config(obj.run_properties), config
    )
    versioning = run_properties.versioning
    ci_branch = versioning.branch
    console = obj.console
    with Repository(config=RepoConfig.from_config(config)) as repo:
        console.print(
            Markdown(f"Repository tracking [{repo.remote_url}]({repo.remote_url})")
            if repo.remote_url
            else Markdown("Repository not tracking any remote origin")
        )

        console.print(
            Markdown(
                f"Branch as specified in _{DEFAULT_RUN_PROPERTIES_FILE_NAME}_: `{ci_branch}`"
                if ci_branch
                else f"No branch specified at `build.versioning.branch` in _{DEFAULT_RUN_PROPERTIES_FILE_NAME}_"
            )
        )
        if not repo.has_valid_head:
            console.log(
                Markdown(
                    f"Current branch `{repo.get_branch}` does **not** point to a valid reference."
                )
            )
            return

        console.log(
            Markdown(
                f"Current branch: `{repo.get_branch}` at `{repo.get_sha}`"
                if repo.get_branch
                else "Head of current branch is detached"
            )
        )
        base_revision = repo.base_revision
        console.line(1)
        console.log(Markdown(f"Configured base branch: `{repo.main_origin_branch}`"))
        if repo.get_branch == repo.main_branch:
            if versioning.tag:
                if not repo.fit_for_tag_build(versioning.tag):
                    console.log("❌ Repo not fit for tag build")
                else:
                    changes = repo.changes_in_tagged_commit(versioning.tag)
                    files_changed = changes[0].files_touched
                    console.log(
                        Markdown(
                            f"*{len(files_changed)}* files changed in merge commit `{versioning.tag}`"
                        )
                    )
            else:
                console.log(f"On main branch ({repo.main_branch}), no tag specified.")
            return

        if base_revision:
            console.log(
                Markdown(
                    f"Base revision is `{base_revision.name_rev}` by _{base_revision.author}_ at "
                    f"{base_revision.committed_datetime}"
                )
            )
            changes = repo.changes_between(base_revision.hexsha, repo.get_sha)
            console.log(
                Markdown(
                    f"{len(changes)} commits between `{repo.main_origin_branch}` and `{repo.get_branch}`"
                )
            )
        else:
            changes = repo.changes_in_branch()
            console.log(
                Markdown(
                    f"Revision for `{repo.main_origin_branch}` not found. Cannot diff with base. "
                    f"*{len(changes)}* (grafted) commits on `{repo.get_branch}`"
                )
            )


def create_repo(config: dict) -> tuple[Repository, dict]:
    return Repository(config=RepoConfig.from_config(config)), config


@repository.command(help="Initialize the repository for a build run")
@click.option("--url", "-u", type=click.STRING, help="URL to the remote repository")
@click.option("--pull", "-pr", type=click.INT, help="PR number to fetch")
@click.option("--branch", "-b", type=click.STRING, help="Branch to fetch")
@click.option(
    "--pristine",
    "-p",
    is_flag=True,
    default=False,
    help="When set, the local folder is assumed to be empty and a `git clone` "
    "will be performed instead of pulling the latest changes from the remote.",
)
@click.pass_obj
def init(obj: RepoContext, url: str, pull: int, branch: str, pristine: bool):
    console = obj.console

    console.log("Preparing repository for a new run...")

    with Repository.from_shallow_diff_clone(
        branch.replace("refs/heads/", ""), url, "main", obj.config, Path(".")
    ) if pristine else Repository(
        config=RepoConfig.from_config(parse_config(obj.config))
    ) as repo:
        config = parse_config(obj.config)
        if not repo.remote_url:
            with console.status("👷 Initializing remote origin") as progress:
                repo_config = RepoConfig.from_config(config).repo_credentials
                url = url or (repo_config and repo_config.to_url_with_credentials)
                remote = repo.init_remote(url)
                progress.console.log(f"👷 Remote initialized at {remote.url}")

        console.log(f"✅ Repository tracking {repo.remote_url}")

        properties = RunProperties.from_configuration(
            parse_config(obj.run_properties), config
        )
        pr_number = pull or properties.versioning.pr_number

        if pr_number:
            target_branch = (
                f"PR-{pr_number}"
                if pr_number
                else branch or properties.versioning.branch
            )
            console.log(Markdown(f"Initializing `{target_branch}`..."))
            repo.fetch_main_branch()

            if repo.get_branch != target_branch:
                with console.status(f"👷 Fetching PR #{pr_number}"):
                    if repo.local_branch_exists(target_branch):
                        console.log(
                            Markdown(
                                f"👷 Deleting local branch to prevent conflicts `{target_branch}`"
                            )
                        )
                        repo.delete_local_branch(target_branch)

                    repo.fetch_pr(pr_number)
                    repo.checkout_branch(target_branch)
                    console.log(
                        Markdown(f"✅ Fetched PR #{pr_number} to `{target_branch}`")
                    )
            else:
                console.log(Markdown(f"✅ HEAD is on `{target_branch}`"))
            with console.status("Finding base"):
                base_revision = repo.base_revision
                if not base_revision:
                    repo.fetch_main_branch()

                console.log(
                    Markdown(
                        f"✅ Found base `{repo.main_origin_branch}` at `{repo.base_revision}`"
                    )
                )
