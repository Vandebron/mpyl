"""Commands related to projects and how they relate"""
import click

from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml')
@click.pass_context
def projects(ctx, config):
    """Commands related to projects"""
    parsed_config = parse_config(config)
    ctx.obj = ctx.with_resource(Repository(config=RepoConfig(parsed_config)))


@projects.command(name='list')
@click.pass_obj
def list_projects(repo):
    found_projects = repo.find_projects()
    click.echo(f'projects {found_projects}')


@projects.command()
def lint():
    click.echo('projects list')


if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
