"""Commands related to build"""
import asyncio
import shutil
from pathlib import Path

import click
from click import ParamType, BadParameter
from click.shell_completion import CompletionItem
from rich.console import Console
from rich.markdown import Markdown

from . import CliContext, CONFIG_PATH_HELP, check_updates
from . import create_console_logger
from .commands.build.jenkins import JenkinsRunParameters, run_jenkins
from .commands.build.mpyl import MpylRunParameters, run_mpyl, MpylCliParameters, MpylRunConfig, find_build_set
from ..project import load_project
from ..reporting.formatting.markdown import run_result_to_markdown
from ..steps.models import RunProperties
from ..steps.run import RunResult
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


async def warn_if_update(console: Console):
    update = await check_updates()
    if update:
        console.print(Markdown(f"⚠️  **You can upgrade to {update} :** `pip install -U mpyl=={update}`"))


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help=CONFIG_PATH_HELP,
              envvar="MPYL_CONFIG_PATH", default='mpyl_config.yml')
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.pass_context
def build(ctx, config, verbose):
    """Pipeline build commands"""
    console = create_console_logger(local=False, verbose=verbose)
    parsed_config = parse_config(config)
    repo = ctx.with_resource(Repository(config=RepoConfig(parsed_config)))
    ctx.obj = CliContext(parsed_config, repo, console, verbose)


@build.command(help='Run an MPyL build')
@click.option('--properties', '-p', required=False, type=click.Path(exists=False), help='Path to run properties',
              envvar="MPYL_RUN_PROPERTIES_PATH", default='run_properties.yml')
@click.option('--ci', is_flag=True,
              help='Run as CI build instead of local. Ignores unversioned changes.')
@click.option('--all', 'all_', is_flag=True, help='Build all projects, regardless of changes on branch')
@click.pass_obj
def run(obj: CliContext, properties, ci, all_):  # pylint: disable=invalid-name
    asyncio.run(warn_if_update(obj.console))
    run_properties = RunProperties.from_configuration(parse_config(properties), obj.config) if ci \
        else RunProperties.for_local_run(obj.config, obj.repo.get_sha, obj.repo.get_branch)

    parameters = MpylCliParameters(local=not ci, all=all_, verbose=obj.verbose)
    obj.console.log(parameters)
    run_parameters = MpylRunParameters(
        run_config=MpylRunConfig(config=obj.config, run_properties=run_properties),
        parameters=parameters
    )
    run_mpyl(run_parameters, None)


@build.command(help="The status of the current local branch from MPyL's perspective")
@click.pass_obj
def status(obj: CliContext):
    asyncio.run(warn_if_update(obj.console))
    branch = obj.repo.get_branch
    if obj.repo.main_branch == obj.repo.get_branch:
        obj.console.log(f'On main branch ({branch}), cannot determine build status')
        return

    changes_in_branch = obj.repo.changes_in_branch_including_local()
    build_set = find_build_set(obj.repo, changes_in_branch, False)
    run_properties = RunProperties.for_local_run(obj.config, obj.repo.get_short_sha, obj.repo.get_branch)
    result = RunResult(run_properties=run_properties, run_plan=build_set)
    version = run_properties.versioning
    header: str = f"**Revision:** `{version.branch}` at `{version.revision}`  \n"
    if result.run_plan:
        obj.console.print(Markdown(markup=header + "**Execution plan:**  \n" + run_result_to_markdown(result)))
    else:
        obj.console.print("No changes detected, nothing to do.")


class Pipeline(ParamType):
    name = 'pipeline'

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        if not ctx.parent or ctx.parent.params['config'] is None or not Path(ctx.parent.params['config']).exists():
            raise BadParameter('Either --config parameter must or MPYL_CONFIG_PATH env var must be set', ctx=ctx,
                               param=param)

        config: dict = parse_config(ctx.parent.params['config'])
        parsed_config: dict[str, str] = config['jenkins']['pipelines']

        return [
            CompletionItem(value=pl[0], help=pl[1]) for pl in parsed_config.items() if
            incomplete in pl[0]
        ]


@build.command(help='Run a multi branch pipeline build on Jenkins')
@click.option(
    '--user', '-u',
    help='Authentication API user. Can be set via env var JENKINS_USER',
    envvar="JENKINS_USER",
    type=click.STRING,
    required=True
)
@click.option(
    '--password', '-p',
    help='Authentication API password. Can be set via env var JENKINS_PASSWORD',
    envvar="JENKINS_PASSWORD",
    type=click.STRING,
    required=True
)
@click.option(
    '--pipeline', '-pl',
    help='The pipeline to run. Must be one of the pipelines listed in `jenkins.pipelines`. '
         'Default value is `jenkins.defaultPipeline`',
    type=Pipeline(),
    required=False
)
@click.pass_context
def jenkins(ctx, user, password, pipeline):
    asyncio.run(warn_if_update(ctx.obj.console))
    selected_pipeline = pipeline if pipeline else ctx.obj.config['jenkins']['defaultPipeline']
    run_argument = JenkinsRunParameters(user, password, ctx.obj.config, selected_pipeline, ctx.obj.verbose)
    run_jenkins(run_argument)


@build.command(help='Clean MPyL metadata in `.mpl` folders')
@click.option('--filter', '-f', 'filter_', required=False, type=click.STRING, help='Filter based on filepath ')
@click.pass_obj
def clean(obj: CliContext, filter_):
    found_projects = obj.repo.find_projects(filter_ if filter_ else '')
    for project in found_projects:
        target_path = Path(load_project(obj.repo.root_dir(), Path(project), strict=False).target_path)
        if target_path.exists():
            shutil.rmtree(target_path)
            obj.console.print(f"🧹 Cleaned up {target_path}")


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
