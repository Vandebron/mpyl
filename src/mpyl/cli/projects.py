"""Commands related to projects and how they relate"""
import sys
from dataclasses import dataclass
from pathlib import Path

import click
from click import ParamType, Argument
from click.shell_completion import CompletionItem
from rich.markdown import Markdown
from rich.prompt import Confirm

from . import (
    CliContext,
    CONFIG_PATH_HELP,
    create_console_logger,
    parse_config_from_supplied_location,
)
from .commands.projects.formatting import print_project
from ..cli.commands.projects.lint import (
    _find_project_paths,
    _check_and_load_projects,
    _assert_unique_project_names,
    _assert_correct_project_linkup,
)
from ..cli.commands.projects.upgrade import check_upgrade
from ..constants import DEFAULT_CONFIG_FILE_NAME
from ..project import load_project, Project, Target
from ..projects.versioning import (
    check_upgrades_needed,
    upgrade_file,
    UPGRADERS,
)
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
    """Commands related to MPyL project configurations (project.yml)"""
    console = create_console_logger(show_path=False, verbose=verbose, max_width=0)
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
        name = load_project(obj.cli.repo.root_dir, Path(proj), False).name
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
@click.pass_context
def show_project(ctx, name):
    obj = ctx.obj
    project_path = f"{name}/{Project.project_yaml_path()}"
    if not (obj.cli.repo.root_dir / project_path).exists():
        obj.cli.console.print(
            Markdown(
                f"Project `{name}` not found. 👉 Finding projects is much easier with [auto completion]"
                f"(https://vandebron.github.io/mpyl/mpyl.html#mpyl-cli) enabled."
            )
        )
        complete = ProjectPath().shell_complete(
            ctx, Argument(param_decls=["--name"]), name
        )
        obj.cli.console.print("Did you mean one of these?")
        obj.cli.console.print([file.value for file in complete])
        return
    print_project(obj.cli.repo, obj.cli.console, project_path)


@projects.command(help="Validate the yaml of changed projects against their schema")
@click.option(
    "--all",
    "all_",
    is_flag=True,
    help="Validate all project yaml's, regardless of changes on branch",
)
@click.option(
    "--extended",
    "-e",
    "extended",
    is_flag=True,
    help="Enable extra validations like PR namespace linkup",
)
@click.pass_obj
def lint(obj: ProjectsContext, all_, extended):
    loaded_projects = _check_and_load_projects(
        console=obj.cli.console,
        repo=obj.cli.repo,
        project_paths=_find_project_paths(all_, obj.cli.repo, obj.filter),
        strict=True,
    )
    all_projects = _check_and_load_projects(
        console=None,
        repo=obj.cli.repo,
        project_paths=_find_project_paths(True, obj.cli.repo, ""),
        strict=False,
    )
    _assert_unique_project_names(
        console=obj.cli.console,
        all_projects=all_projects,
    )
    if extended:
        _assert_correct_project_linkup(
            console=obj.cli.console,
            target=Target.PULL_REQUEST,
            projects=all_projects if all_ else loaded_projects,
            all_projects=all_projects,
            pr_identifier=123,
        )


@projects.command(help="Upgrade projects to conform with the latest schema")
@click.option(
    "--apply",
    "-a",
    is_flag=True,
    help="Apply upgrade operations to the project files",
)
@click.pass_obj
def upgrade(obj: ProjectsContext, apply: bool):
    paths = map(Path, _find_project_paths(True, obj.cli.repo, ""))
    candidates = check_upgrades_needed(list(paths))
    if not apply:
        upgradable = check_upgrade(obj.cli.console, candidates)
        number_in_need_of_upgrade = len(upgradable)
        if number_in_need_of_upgrade > 0:
            obj.cli.console.print(
                f"{number_in_need_of_upgrade} projects need to be upgraded"
            )
            sys.exit(1)

    with obj.cli.console.status("Checking for upgrades...") as status:
        materialized = list(candidates)
        need_upgrade = [path for path, diff in materialized if diff is not None]
        number_of_upgrades = len(need_upgrade)
        status.console.print(
            f"Found {len(materialized)} projects, of which {number_of_upgrades} need to be upgraded"
        )
        status.stop()
        if number_of_upgrades > 0 and Confirm.ask("Upgrade all?"):
            status.start()
            for path in need_upgrade:
                status.update(f"Upgrading {path}")
                upgraded = upgrade_file(path, UPGRADERS)
                if upgraded:
                    path.write_text(upgraded)
            status.stop()
            status.console.print(
                Markdown(
                    f"Upgraded {number_of_upgrades} projects. Validate with `mpyl projects lint --extended`"
                )
            )


if __name__ == "__main__":
    projects()  # pylint: disable=no-value-for-parameter
