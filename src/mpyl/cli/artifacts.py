"""Commands to manage remotely cached artifacts"""

import logging
import os
import shutil
from pathlib import Path

import click
from pyaml_env import parse_config

from ..artifacts import BuildArtifacts
from ..cli import CliContext, create_console_logger, CONFIG_PATH_HELP
from ..constants import DEFAULT_CONFIG_FILE_NAME
from ..utilities.github import clone_repository
from ..utilities.repo import Repository, RepoConfig


@click.group("artifacts")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help=CONFIG_PATH_HELP,
    envvar="MPYL_CONFIG_PATH",
    default=DEFAULT_CONFIG_FILE_NAME,
)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.pass_context
def artifacts(ctx: click.Context, config: str, verbose: bool):
    """Manage remote build artifacts"""
    console = create_console_logger(show_path=False, verbose=verbose, max_width=0)
    parsed_config = parse_config(config)
    repo = ctx.with_resource(Repository(config=RepoConfig.from_config(parsed_config)))
    ctx.obj = CliContext(
        config=parsed_config,
        repo=repo,
        console=console,
        verbose=verbose,
        run_properties={},
    )


@artifacts.command(help="Pull build artifacts from remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option("--pr_number", type=click.INT, help="PR number to fetch", required=False)
@click.pass_obj
def pull(obj: CliContext, tag: str, pr_number: int):
    target_branch = tag if tag else f"PR-{pr_number}"
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")

    try:
        build_artifacts = _prepare_artifacts_repo(obj)
        build_artifacts.pull(branch=target_branch)
    finally:
        shutil.rmtree(
            obj.config["vcs"]["artifactRepository"]["folder"], ignore_errors=True
        )


@artifacts.command(help="Push build artifacts to remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option("--pr_number", type=click.INT, help="PR number to fetch", required=False)
@click.pass_obj
def push(obj: CliContext, tag: str, pr_number: int):
    target_branch = tag if tag else f"PR-{pr_number}"
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")

    try:
        build_artifacts = _prepare_artifacts_repo(obj)
        build_artifacts.push(branch=target_branch)
    finally:
        shutil.rmtree(
            obj.config["vcs"]["artifactRepository"]["folder"], ignore_errors=True
        )


def _prepare_artifacts_repo(obj: CliContext) -> BuildArtifacts:
    artifact_repo_config: RepoConfig = RepoConfig.from_git_config(
        obj.config["vcs"]["artifactRepository"]
    )
    if artifact_repo_config.folder and not os.path.exists(
        Path(artifact_repo_config.folder) / ".git"
    ):
        clone_repository(artifact_repo_config)

    logger = logging.getLogger("mpyl")
    artifact_repo = Repository(config=artifact_repo_config)
    return BuildArtifacts(
        logger=logger,
        codebase_repo=obj.repo,
        artifact_repo=artifact_repo,
    )
