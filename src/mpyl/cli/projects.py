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
    _check_and_load_projects,
    _assert_unique_project_names,
    _assert_correct_project_linkup,
    _lint_whitelisting_rules,
    __detail_wrong_substitutions,
)
from ..cli.commands.projects.upgrade import check_upgrade
from ..constants import DEFAULT_CONFIG_FILE_NAME
from ..project import load_project, Project, Target, get_project_root_dir
from ..projects.versioning import (
    check_upgrades_needed,
    upgrade_file,
    PROJECT_UPGRADERS,
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


OVERRIDE_PATTERN = "project-override"


@projects.command(name="list", help="List found projects")
@click.pass_obj
def list_projects(obj: ProjectsContext):
    found_projects = obj.cli.repo.find_projects(obj.filter)

    for proj in found_projects:
        if OVERRIDE_PATTERN not in proj:
            project = load_project(obj.cli.repo.root_dir, Path(proj), False)
            obj.cli.console.print(Markdown(f"{proj} `{project.name}`"))


@projects.command(name="names", help="List found project names")
@click.pass_obj
def list_project_names(obj: ProjectsContext):
    found_projects = obj.cli.repo.find_projects(obj.filter)

    names = sorted(
        [
            load_project(obj.cli.repo.root_dir, Path(proj), False).name
            for proj in found_projects
            if OVERRIDE_PATTERN not in proj
        ]
    )

    for name in names:
        obj.cli.console.print(name)


class ProjectPath(ParamType):
    name = "project_path"

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        parsed_config = parse_config_from_supplied_location(ctx, param)
        repo = ctx.with_resource(
            Repository(config=RepoConfig.from_config(parsed_config))
        )
        found_projects = repo.find_projects(incomplete)
        return [
            CompletionItem(value=get_project_root_dir(proj)) for proj in found_projects
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
@click.pass_obj
def lint(obj: ProjectsContext):
    loaded_projects = _check_and_load_projects(
        console=obj.cli.console,
        repo=obj.cli.repo,
        project_paths=obj.cli.repo.find_projects(obj.filter),
        strict=True,
    )
    all_projects = (
        _check_and_load_projects(
            console=None,
            repo=obj.cli.repo,
            project_paths=obj.cli.repo.find_projects(""),
            strict=False,
        )
        if obj.filter != ""
        else loaded_projects
    )
    _assert_unique_project_names(
        console=obj.cli.console,
        all_projects=all_projects,
    )

    obj.cli.console.print("")
    obj.cli.console.print("Running extended checks...")

    failed = False
    wrong_substitutions = _assert_correct_project_linkup(
        console=obj.cli.console,
        target=Target.PULL_REQUEST,
        projects=loaded_projects,
        all_projects=all_projects,
        pr_identifier=123,
    )
    if len(wrong_substitutions) == 0:
        obj.cli.console.print("  ✅ No wrong namespace substitutions found")
    else:
        failed = True
        __detail_wrong_substitutions(obj.cli.console, all_projects, wrong_substitutions)

    for target in Target:
        wrong_whitelists = _lint_whitelisting_rules(
            console=obj.cli.console,
            projects=loaded_projects,
            config=obj.cli.config,
            target=target,
        )
        if len(wrong_whitelists) == 0:
            obj.cli.console.print("  ✅ No undefined whitelists found")
        else:
            for project, diff in wrong_whitelists:
                obj.cli.console.log(
                    f"  ❌ Project {project.name} has undefined whitelists: {diff}"
                )
                failed = True

    if failed:
        click.get_current_context().exit(1)


@projects.command(help="Upgrade projects to conform with the latest schema")
@click.option(
    "--apply",
    "-a",
    is_flag=True,
    help="Apply upgrade operations to the project files",
)
@click.pass_obj
def upgrade(obj: ProjectsContext, apply: bool):
    paths = map(Path, obj.cli.repo.find_projects(""))
    candidates = check_upgrades_needed(list(paths), PROJECT_UPGRADERS)
    console = obj.cli.console
    if not apply:
        upgradable = check_upgrade(console, candidates)
        number_in_need_of_upgrade = len(upgradable)
        if number_in_need_of_upgrade > 0:
            console.print(f"{number_in_need_of_upgrade} projects need to be upgraded")
            sys.exit(1)

    with console.status("Checking for upgrades...") as status:
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
                upgraded = upgrade_file(path, PROJECT_UPGRADERS)
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
