"""Commands related to build"""
import click

from ..build.jenkins import JenkinsRunParameters, run_build


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml')
@click.pass_context
def build(ctx, config):
    """Pipeline build commands"""
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["config_path"] = config


@build.command()
def status():
    click.echo('build status')


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
@click.pass_obj
def run(obj, user, password):
    run_argument = JenkinsRunParameters(user, password, obj['config_path'], 'mpyl-test')
    run_build(run_argument)


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
