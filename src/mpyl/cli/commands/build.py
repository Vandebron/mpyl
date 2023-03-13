"""Commands related to build"""
from typing import Any, Optional

import click

from ..build.jenkins import JenkinsRunParameters, run_build
from ...utilities.pyaml_env import parse_config


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml')
@click.pass_context
def build(ctx, config):
    """Pipeline build commands"""
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["config"] = parse_config(config)


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
            self, value: Any, param: Optional["Parameter"], ctx: Optional["Context"]
    ) -> Any:
        parsed = ctx.obj['config']
        if value is None:
            value = parsed['jenkins']['defaultPipeline']
        self.choices = parsed['jenkins']['pipelines'].keys()
        return super().convert(value, param, ctx)


@build.command()
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
def run(obj, user, password, pipeline):
    run_argument = JenkinsRunParameters(user, password, obj['config'], pipeline)
    run_build(run_argument)


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
