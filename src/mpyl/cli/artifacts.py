"""Commands to manage remotely cached artifacts"""

import logging
from pathlib import Path

import click
from pyaml_env import parse_config

from ..artifacts.build_artifacts import ArtifactsRepository, ManifestPathTransformer
from ..cli import CliContext, create_console_logger, CONFIG_PATH_HELP
from ..constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from ..project import Project
from ..steps.deploy.k8s import DeployConfig
from ..steps.models import RunProperties
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
def artifacts(ctx: click.Context, config: str, properties: str, verbose: bool):
    """Manage remote build artifacts"""
    console = create_console_logger(show_path=False, verbose=verbose, max_width=0)
    parsed_config = parse_config(config)
    parsed_properties = parse_config(properties)
    repo = ctx.with_resource(Repository(config=RepoConfig.from_config(parsed_config)))
    ctx.obj = CliContext(
        config=parsed_config,
        repo=repo,
        console=console,
        verbose=verbose,
        run_properties=parsed_properties,
    )


@artifacts.command(help="Pull build artifacts from remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option(
    "--pr_number", "-pr", type=click.INT, help="PR number to fetch", required=False
)
@click.pass_obj
def pull(obj: CliContext, tag: str, pr_number: int):
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    target_branch = (
        tag if tag else f"PR-{pr_number or run_properties.versioning.pr_number}"
    )
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")

    build_artifacts = _prepare_artifacts_repo(obj=obj, repo_path=Path("."))
    build_artifacts.pull(branch=target_branch)


@artifacts.command(help="Push build artifacts to remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option(
    "--pr_number", "-pr", type=click.INT, help="PR number to fetch", required=False
)
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=False),
    help="Path within repository to copy artifacts to",
    required=True,
)
@click.pass_obj
def push(obj: CliContext, tag: str, pr_number: int, path: Path):
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    target_branch = (
        tag if tag else f"PR-{pr_number or run_properties.versioning.pr_number}"
    )
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")

    build_artifacts = _prepare_artifacts_repo(obj=obj, repo_path=path)
    deploy_config = DeployConfig.from_config(obj.config)
    manifest_paths = [
        Path(project.replace(Project.project_yaml_path(), deploy_config.output_path))
        for project in obj.repo.find_projects()
    ]

    build_artifacts.push(
        branch=target_branch,
        file_paths=[path for path in manifest_paths if path.exists()],
        path_transformer=ManifestPathTransformer(),
    )


def _prepare_artifacts_repo(obj: CliContext, repo_path: Path) -> ArtifactsRepository:
    git_config = obj.config["vcs"].get("artifactRepository", None)
    if not git_config:
        raise ValueError("No artifact repository configured")
    artifact_repo_config: RepoConfig = RepoConfig.from_git_config(git_config=git_config)
    logger = logging.getLogger("mpyl")

    return ArtifactsRepository(
        logger=logger,
        codebase_repo=obj.repo,
        artifact_repo_config=artifact_repo_config,
        path_within_artifact_repo=repo_path,
    )
