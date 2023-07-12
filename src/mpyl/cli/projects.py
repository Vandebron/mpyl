"""Commands related to projects and how they relate"""
from dataclasses import dataclass
from pathlib import Path

import click
import jsonschema
from click import ParamType
from click.shell_completion import CompletionItem
from rich.markdown import Markdown

from . import (
    CliContext,
    CONFIG_PATH_HELP,
    create_console_logger,
    parse_config_from_supplied_location,
)
from .commands.projects.formatting import print_project
from .commands.build.mpyl import find_build_set
from ..constants import DEFAULT_CONFIG_FILE_NAME
from ..project import validate_project, load_project, Project
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


@dataclass
class ProjectsContext:
    cli: CliContext
    filter: str


@click.group("projects")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help=CONFIG_PATH_HELP,
    envvar="MPYL_CONFIG_PATH",
    default=DEFAULT_CONFIG_FILE_NAME,
)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.option(
    "--filter",
    "-f",
    "filter_",
    required=False,
    type=click.STRING,
    help="Filter based on filepath ",
)
@click.pass_context
def projects(ctx, config, verbose, filter_):
    """Commands related to projects"""
    console = create_console_logger(local=False, verbose=verbose)
    parsed_config = parse_config(config)
    ctx.obj = ProjectsContext(
        cli=CliContext(
            config=parsed_config,
            repo=ctx.with_resource(
                Repository(config=RepoConfig.from_config(parsed_config))
            ),
            console=console,
            verbose=verbose,
            run_properties={},
        ),
        filter=filter_ if filter_ else "",
    )


@projects.command(name="list", help="List found projects")
@click.pass_obj
def list_projects(obj: ProjectsContext):
    found_projects = obj.cli.repo.find_projects(obj.filter)

    for proj in found_projects:
        name = load_project(obj.cli.repo.root_dir(), Path(proj), False).name
        obj.cli.console.print(Markdown(f"{proj} `{name}`"))


class ProjectPath(ParamType):
    name = "project_path"

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        parsed_config = parse_config_from_supplied_location(ctx, param)
        repo = ctx.with_resource(
            Repository(config=RepoConfig.from_config(parsed_config))
        )
        found_projects = repo.find_projects(incomplete)
        return [
            CompletionItem(value=proj.replace(f"/{Project.project_yaml_path()}", ""))
            for proj in found_projects
        ]


@projects.command(name="show", help="Show details of a project")
@click.argument("name", required=True, type=ProjectPath())
@click.pass_obj
def show_project(obj, name):
    print_project(
        obj.cli.repo, obj.cli.console, f"{name}/{Project.project_yaml_path()}"
    )


@projects.command(help="Validate the yaml of changed projects against their schema")
@click.option(
    "--all",
    "all_",
    is_flag=True,
    help="Validate all project yaml's, regardless of changes on branch",
)
@click.pass_obj
def lint(obj: ProjectsContext, all_):
    project_paths = []
    if all_:
        project_paths = obj.cli.repo.find_projects(obj.filter)
    else:
        branch = obj.cli.repo.get_branch
        changes = (
            obj.cli.repo.changes_in_branch_including_local()
            if branch
            else obj.cli.repo.changes_in_merge_commit()
        )
        build_set = find_build_set(obj.cli.repo, changes, False)
        for all_projects in build_set.values():
            for project in all_projects:
                project_paths.append(project.path)

    invalid = 0
    valid = 0
    for project_path in set(project_paths):
        try:
            path = Path(obj.cli.repo.root_dir()) / Path(project_path)
            with open(path, encoding="utf-8") as file:
                validate_project(file)
        except jsonschema.exceptions.ValidationError as exc:
            obj.cli.console.print(f"❌ {project_path}: {exc.message}")
            invalid += 1
        else:
            valid += 1
            if obj.cli.verbose:
                obj.cli.console.print(f"✅ {project_path}")
    obj.cli.console.print(
        f"Validated {valid + invalid} projects. {valid} valid, {invalid} invalid"
    )
    if invalid > 0:
        click.get_current_context().exit(1)


if __name__ == "__main__":
    projects()  # pylint: disable=no-value-for-parameter
