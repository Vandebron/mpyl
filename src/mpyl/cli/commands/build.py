"""Commands related to build"""
from typing import Any, Optional

import click
from click import Parameter, Context
from rich.markdown import Markdown

from . import CliContext
from .. import create_console_logger
from ..build.jenkins import JenkinsRunParameters, run_jenkins
from ..build.mpyl import MpylRunParameters, run_mpyl, MpylCliParameters, MpylRunConfig, find_build_set
from ...reporting.formatting.markdown import run_result_to_markdown
from ...steps.models import RunProperties
from ...steps.run import RunResult
from ...utilities.pyaml_env import parse_config
from ...utilities.repo import Repository, RepoConfig


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml',
              envvar="MPYL_CONFIG_PATH", default='config.yml')
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
@click.option('--local', '-l', is_flag=True, default=True, help='Local vs CI build')
@click.option('--all', 'all_', is_flag=True, default=False, help='Build all projects, regardless of changes on branch')
@click.pass_obj
def run(obj, properties, local, all_, verbose):
    run_properties = RunProperties.for_local_run(obj.config, obj.repo.get_sha, obj.repo.get_branch) if local \
        else RunProperties.from_configuration(parse_config(properties), obj.config)

    run_parameters = MpylRunParameters(
        run_config=MpylRunConfig(config=obj.config, run_properties=run_properties),
        parameters=MpylCliParameters(local=local, all=all_, verbose=verbose)
    )
    run_mpyl(run_parameters, None)


@build.command(help="The status of the current local branch from MPyL's perspective")
@click.pass_obj
def status(obj: CliContext):
    changes_in_branch = obj.repo.changes_in_branch_including_local()
    build_set = find_build_set(obj.repo, changes_in_branch, False)
    run_properties = RunProperties.for_local_run(obj.config, obj.repo.get_short_sha, obj.repo.get_branch)
    result = RunResult(run_properties=run_properties, run_plan=build_set)
    version = run_properties.versioning
    header: str = f"**Revision:** `{version.branch}` at `{version.revision}`  \n"
    obj.console.print(Markdown(markup=header + "**Execution plan:**  \n" + run_result_to_markdown(result)))


def get_default(ctx):
    if not ctx:
        return 'config.jenkins.defaultPipeline'

    return ctx.obj.config['jenkins']['defaultPipeline']


class DynamicChoice(click.Choice):
    def __init__(self):
        super().__init__([])

    def convert(
            self, value: Any, param: Optional[Parameter], ctx: Optional[Context]
    ) -> Any:
        if ctx is None:
            raise KeyError("Context needs to be set. Did you use @click.pass_context in the parent group?")

        config = ctx.obj.config
        if value is None:
            value = config['jenkins']['defaultPipeline']
        self.choices = config['jenkins']['pipelines'].keys()
        return super().convert(value, param, ctx)


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
         'Default value is `jenkins.defaultPipeline',
    type=DynamicChoice(),
    required=True,
    default=lambda: get_default(click.get_current_context(silent=True))
)
@click.pass_obj
def jenkins(obj, user, password, pipeline):
    run_argument = JenkinsRunParameters(user, password, obj.config, pipeline)
    run_jenkins(run_argument)


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
