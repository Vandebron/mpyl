import click
from pyaml_env import parse_config

from ..artifacts import Artifacts
from ..cli import CliContext, create_console_logger, CONFIG_PATH_HELP
from ..constants import DEFAULT_CONFIG_FILE_NAME
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
def artifacts(ctx, config, verbose):
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


@artifacts.command(help="Pull artifacts")
@click.option("--tag", "-t", help="Tag to build", type=click.STRING, required=False)
@click.option("--pr", type=click.INT, help="PR number to fetch", required=False)
@click.pass_obj
def pull(obj: CliContext, tag, pr):
    target_branch = tag if tag else f"PR-{pr}"
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")
    print("inside pull: ", obj.config)
    print("inside pull: ", target_branch)


@artifacts.command(help="Push artifacts")
@click.option("--tag", "-t", help="Tag to build", type=click.STRING, required=False)
@click.option("--pr", type=click.INT, help="PR number to fetch", required=False)
@click.pass_obj
def push(obj: CliContext, tag, pr):
    target_branch = tag if tag else f"PR-{pr}"
    if not target_branch:
        raise click.ClickException("Either --pr or --tag must be specified")
    print("inside push: ", obj.config)
    print("inside push: ", target_branch)
    Artifacts(obj.repo).push(branch=target_branch)
