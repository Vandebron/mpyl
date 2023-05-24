"""Commands related to projects and how they relate"""
from dataclasses import dataclass
from pathlib import Path

import click
import jsonschema
from click import ParamType, BadParameter
from click.shell_completion import CompletionItem
from rich.markdown import Markdown

from ..constants import DEFAULT_CONFIG_FILE_NAME
from . import CliContext, CONFIG_PATH_HELP, create_console_logger
from .commands.projects.formatting import print_project
from ..project import validate_project, load_project, Project
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


@dataclass
class ProjectsContext:
    cli: CliContext
    filter: str


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help=CONFIG_PATH_HELP,
              envvar="MPYL_CONFIG_PATH", default=DEFAULT_CONFIG_FILE_NAME)
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.option('--filter', '-f', 'filter_', required=False, type=click.STRING, help='Filter based on filepath ')
@click.pass_context
def projects(ctx, config, verbose, filter_):
    """Commands related to projects"""
    console = create_console_logger(local=False, verbose=verbose)
    parsed_config = parse_config(config)
    ctx.obj = ProjectsContext(
        cli=CliContext(config=parsed_config, repo=ctx.with_resource(Repository(config=RepoConfig(parsed_config))),
                       console=console, verbose=verbose), filter=filter_ if filter_ else '')


@projects.command(name='list', help='List found projects')
@click.pass_obj
def list_projects(obj: ProjectsContext):
    found_projects = obj.cli.repo.find_projects(obj.filter)

    for proj in found_projects:
        name = load_project(obj.cli.repo.root_dir(), Path(proj), False).name
        obj.cli.console.print(Markdown(f"{proj} `{name}`"))


class ProjectPath(ParamType):
    name = 'project_path'

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        if not ctx.parent or ctx.parent.params['config'] is None or not Path(ctx.parent.params['config']).exists():
            raise BadParameter('Either --config parameter must or MPYL_CONFIG_PATH env var must be set', ctx=ctx,
                               param=param)

        parsed_config = parse_config(ctx.parent.params['config'])
        repo = ctx.with_resource(Repository(config=RepoConfig(parsed_config)))
        found_projects = repo.find_projects(incomplete)
        return [
            CompletionItem(value=proj.replace(f'/{Project.project_yaml_path()}', ''))
            for proj in found_projects
        ]


@projects.command(name='show', help='Show details of a project')
@click.argument('name', required=True, type=ProjectPath())
@click.pass_obj
def show_project(obj, name):
    print_project(obj.cli.repo, obj.cli.console, f'{name}/{Project.project_yaml_path()}')


@projects.command(help='Validate the yaml of found projects against their schema')
@click.pass_obj
def lint(obj: ProjectsContext):
    found_projects = obj.cli.repo.find_projects(obj.filter)
    invalid = 0
    valid = 0
    for project in found_projects:
        try:
            project_path = Path(obj.cli.repo.root_dir()) / Path(project)
            with open(project_path, encoding='utf-8') as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            obj.cli.console.print(f'❌ {project}: {exc.message}')
            invalid += 1
        else:
            valid += 1
            if obj.cli.verbose:
                obj.cli.console.print(f'✅ {project}')
    obj.cli.console.print(f'Validated {valid + invalid} projects. {valid} valid, {invalid} invalid')
    if invalid > 0:
        click.get_current_context().exit(1)

if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
