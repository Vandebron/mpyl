"""Commands related to projects and how they relate"""
import logging
from dataclasses import dataclass
from logging import Logger
from pathlib import Path

import click
import jsonschema

from .. import set_cli_logger
from ...project import validate_project
from ...utilities.pyaml_env import parse_config
from ...utilities.repo import Repository, RepoConfig


@dataclass(frozen=True)
class ProjectsContext:
    config: dict
    repo: Repository
    logger: Logger


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config.yml',
              envvar="MPYL_CONFIG_PATH", default='config.yml')
@click.pass_context
def projects(ctx, config):
    """Commands related to projects"""
    parsed_config = parse_config(config)
    set_cli_logger(local=False, verbose=False)
    ctx.obj = ProjectsContext(parsed_config, ctx.with_resource(Repository(config=RepoConfig(parsed_config))),
                              logger=logging.getLogger())


@projects.command(name='list', help='List found projects')
@click.pass_obj
def list_projects(obj: ProjectsContext):
    found_projects = obj.repo.find_projects()
    for proj in sorted(found_projects):
        obj.logger.info(proj)


@projects.command(help='Validate the yaml of found projects against their schema')
@click.pass_obj
def lint(obj: ProjectsContext):
    found_projects: set[str] = obj.repo.find_projects()
    for project in sorted(found_projects):
        try:
            project_path = Path('.') / Path(project)
            with open(project_path, encoding='utf-8') as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            obj.logger.info(f'❌ {project}: {exc.message}')
        else:
            obj.logger.info(f'✅ {project}')


if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
