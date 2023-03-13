"""Commands related to projects and how they relate"""
from pathlib import Path

import click
import jsonschema

from ...project import validate_project
from ...utilities.pyaml_env import parse_config
from ...utilities.repo import Repository, RepoConfig


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml',
              default='config.yml')
@click.pass_context
def projects(ctx, config):
    """Commands related to projects"""
    parsed_config = parse_config(config)
    ctx.obj = ctx.with_resource(Repository(config=RepoConfig(parsed_config)))


@projects.command(name='list', help='List found projects')
@click.pass_obj
def list_projects(repo):
    found_projects = repo.find_projects()
    for proj in found_projects:
        click.echo(proj)


@projects.command(help='Validate the yaml of found projects against their schema')
@click.pass_obj
def lint(repo):
    found_projects: set[str] = repo.find_projects()
    for project in found_projects:
        try:
            project_path = Path('.') / Path(project)
            with open(project_path, encoding='utf-8') as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            click.echo(f'❌ {project}: {exc.message}')
        else:
            click.echo(f'✅ {project}')


if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
