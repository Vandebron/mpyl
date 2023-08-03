"""Commands related to the CSV (git) repository"""
import click
from rich.markdown import Markdown

from . import (
    CliContext,
    CONFIG_PATH_HELP,
    create_console_logger,
)
from ..constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from ..steps.models import RunProperties
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


@click.group("repo")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
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
    console = create_console_logger(local=False, verbose=verbose)
    ctx.obj = CliContext(
        config=(parse_config(config)),
        repo=ctx.with_resource(
            Repository(config=RepoConfig.from_config(parse_config(config)))
        ),
        console=console,
        verbose=verbose,
        run_properties=(parse_config(properties)),
    )


@repository.command(help="The status of the current local repository")
@click.pass_obj
def status(obj: CliContext):
    """Print the status of the current repository"""
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    console = obj.console
    repo = obj.repo

    console.print(
        Markdown(f"Repository tracking [{repo.remote_url}]({repo.remote_url})")
        if repo.remote_url
        else Markdown("Repository not tracking any remote origin")
    )
    ci_branch = run_properties.versioning.branch

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
        console.log(f"On main branch ({repo.main_branch})")
        return
    if base_revision:
        console.log(
            Markdown(
                f"Locally `{repo.main_origin_branch}` is at _{base_revision.hexsha}_ by _{base_revision.author}_ at "
                f"{base_revision.committed_datetime}"
            )
        )
        changes = obj.repo.changes_between(base_revision.hexsha, repo.get_sha)
        console.log(
            f"{len(changes)} commits between `{repo.main_origin_branch}` and `{repo.get_branch}`"
        )
    else:
        console.log(
            Markdown(
                f"Revision for `{repo.main_origin_branch}` not found. Cannot diff with base"
            )
        )
