"""Commands related to build"""
from typing import Any, Optional

import click
from click import Parameter, Context

from ..build.jenkins import JenkinsRunParameters, run_jenkins
from ..build.mpyl import MpylRunParameters, run_mpyl, MpylCliParameters, MpylRunConfig
from ...utilities.pyaml_env import parse_config


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml',
              default='config.yml')
@click.pass_context
def build(ctx, config):
    """Pipeline build commands"""
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["config"] = parse_config(config)


@build.command(help='Run an MPyL build')
@click.option('--properties', '-p', required=True, type=click.Path(exists=True), help='Path to run properties',
              default='run_properties.yml')
@click.option('--local', '-l', is_flag=True, default=True, help='Local vs CI build')
@click.option('--all', 'all_', is_flag=True, default=False, help='Build all projects, regardless of changes on branch')
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.pass_obj
def run(obj, properties, local, all_, verbose):
    run_parameters = MpylRunParameters(
        run_config=MpylRunConfig(config=obj['config'], run_properties=parse_config(properties)),
        parameters=MpylCliParameters(local=local, all=all_, verbose=verbose)
    )
    run_mpyl(run_parameters, None)


@build.command()
def status():
    click.echo('build status')


def get_default(ctx):
    if not ctx:
        return 'config.jenkins.defaultPipeline'

    return ctx.obj['config']['jenkins']['defaultPipeline']


class DynamicChoice(click.Choice):
    def __init__(self):
        super().__init__([])

    def convert(
            self, value: Any, param: Optional[Parameter], ctx: Optional[Context]
    ) -> Any:
        if ctx is None:
            raise KeyError("Context needs to be set. Did you use @click.pass_context in the parent group?")

        config = ctx.obj['config']
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
    run_argument = JenkinsRunParameters(user, password, obj['config'], pipeline)
    run_jenkins(run_argument)


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
