"""Commands related to projects and how they relate"""
from dataclasses import dataclass
from pathlib import Path

import click
import jsonschema
from rich.markdown import Markdown
from rich.table import Table

from . import CliContext, CONFIG_PATH_HELP
from .. import create_console_logger
from ...project import validate_project, load_project
from ...utilities.pyaml_env import parse_config
from ...utilities.repo import Repository, RepoConfig


@dataclass
class ProjectsContext:
    cli: CliContext
    filter: str


@click.group('projects')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help=CONFIG_PATH_HELP,
              envvar="MPYL_CONFIG_PATH", default='config.yml')
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

    if len(found_projects) == 1:
        project = found_projects[0]
        text = Path(project).read_text(encoding='utf-8')
        obj.cli.console.print(Markdown(f'```yaml\n{text}```', inline_code_lexer='yaml'))
        info = load_project(Path("."), Path(project), False)

        table = Table(title=f"Project {info.name}", show_header=False)
        table.add_row("Name", info.name)
        table.add_row("Path", info.path)
        table.add_row("Description", info.description)
        table.add_row("Maintainer", f"{info.maintainer}")
        table.add_row("Stages", f"{info.stages}")
        obj.cli.console.print(table)
    else:
        for proj in found_projects:
            name = load_project(Path("."), Path(proj), False).name
            obj.cli.console.print(Markdown(f"{proj} `{name}`"))


@projects.command(help='Validate the yaml of found projects against their schema')
@click.pass_obj
def lint(obj: ProjectsContext):
    for project in obj.cli.repo.find_projects(obj.filter):
        try:
            project_path = Path('.') / Path(project)
            with open(project_path, encoding='utf-8') as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            obj.cli.console.print(f'❌ {project}: {exc.message}')
        else:
            obj.cli.console.print(f'✅ {project}')


if __name__ == '__main__':
    projects()  # pylint: disable=no-value-for-parameter
