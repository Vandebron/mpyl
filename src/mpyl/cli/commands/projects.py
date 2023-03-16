"""Commands related to projects and how they relate"""
from pathlib import Path

import click
import jsonschema

from . import CliContext
from .. import create_console_logger
from ...project import validate_project
from ...utilities.pyaml_env import parse_config
from ...utilities.repo import Repository, RepoConfig


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to the config.yml',
              envvar="MPYL_CONFIG_PATH", default='config.yml')
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.pass_context
def projects(ctx, config, verbose):
    """Commands related to projects"""
    console = create_console_logger(local=False, verbose=verbose)
    parsed_config = parse_config(config)
    ctx.obj = CliContext(parsed_config, ctx.with_resource(Repository(config=RepoConfig(parsed_config))), console,
                         verbose)


@projects.command(name='list', help='List found projects')
@click.pass_obj
def list_projects(obj: CliContext):
    found_projects = obj.repo.find_projects()
    for proj in found_projects:
        obj.console.log(proj)


@projects.command(help='Validate the yaml of found projects against their schema')
@click.pass_obj
def lint(obj: CliContext):
    for project in obj.repo.find_projects():
        try:
            project_path = Path('.') / Path(project)
            with open(project_path, encoding='utf-8') as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            obj.console.log(f'❌ {project}: {exc.message}')
        else:
            obj.console.log(f'✅ {project}')


if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
