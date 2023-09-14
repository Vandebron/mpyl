"""Commands related to build"""
import asyncio
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
import questionary
from click import ParamType
from click.shell_completion import CompletionItem
from github import Github
from github.GitRelease import GitRelease
from questionary import Choice
from rich.console import Console
from rich.markdown import Markdown

from . import (
    CliContext,
    CONFIG_PATH_HELP,
    check_updates,
    get_meta_version,
    parse_config_from_supplied_location,
)
from . import create_console_logger
from .commands.build.jenkins import JenkinsRunParameters, run_jenkins, get_token
from ..build import (
    run_mpyl,
    MpylCliParameters,
    get_build_plan,
)
from ..constants import (
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_RUN_PROPERTIES_FILE_NAME,
    BUILD_ARTIFACTS_FOLDER,
)
from ..project import load_project, Target
from ..reporting.formatting.markdown import (
    execution_plan_as_markdown,
)
from ..steps.models import RunProperties
from ..utilities.github import GithubConfig
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


async def warn_if_update(console: Console):
    version = get_meta_version()
    update = await check_updates(meta=version)
    if update:
        console.print(
            Markdown(
                f"⚠️  **You can upgrade from {version} to {update} :** `pip install -U mpyl=={update}`. "
                f"After upgrading, you may need to run `mpyl projects upgrade` to upgrade your projects."
            )
        )


@click.group("build")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help=CONFIG_PATH_HELP,
    envvar="MPYL_CONFIG_PATH",
    default=DEFAULT_CONFIG_FILE_NAME,
)
@click.option(
    "--properties",
    "-p",
    required=False,
    type=click.Path(exists=False),
    help="Path to run properties",
    envvar="MPYL_RUN_PROPERTIES_PATH",
    default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
    show_default=True,
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    show_default=True,
    help="Verbose output",
)
@click.pass_context
def build(ctx, config, properties, verbose):
    """Pipeline build commands"""
    parsed_properties = parse_config(properties)
    parsed_config = parse_config(config)
    console_config = RunProperties.from_configuration(
        parsed_properties, parsed_config
    ).console
    console = create_console_logger(
        show_path=console_config.show_paths,
        verbose=verbose,
        max_width=console_config.width,
    )

    repo = ctx.with_resource(Repository(config=RepoConfig.from_config(parsed_config)))
    ctx.obj = CliContext(parsed_config, repo, console, verbose, parsed_properties)


@build.command(help="Run an MPyL build")
@click.option(
    "--ci",
    is_flag=True,
    help="Run as CI build instead of local. Ignores untracked changes.",
)
@click.option(
    "--all",
    "all_",
    is_flag=True,
    help="Build all projects, regardless of changes on branch",
)
@click.option("--tag", "-t", help="Tag to build", type=click.STRING, required=False)
@click.pass_obj
def run(obj: CliContext, ci, all_, tag):  # pylint: disable=invalid-name
    asyncio.run(warn_if_update(obj.console))

    parameters = MpylCliParameters(
        local=not ci,
        pull_main=all_,
        all=all_,
        verbose=obj.verbose,
        tag=tag,
    )
    obj.console.log(parameters)

    if tag and not obj.repo.fit_for_tag_build(tag):
        obj.console.print(
            Markdown(
                f"Current state of repo is not fit for building tag `{tag}`."
                f"Validate the status of the repo by running `mpyl repo status`."
            )
        )
        sys.exit(1)

    run_properties = (
        RunProperties.from_configuration(obj.run_properties, obj.config, tag)
        if ci
        else RunProperties.for_local_run(
            obj.config, obj.repo.get_sha, obj.repo.get_branch, tag
        )
    )
    result = run_mpyl(
        run_properties=run_properties, cli_parameters=parameters, reporter=None
    )
    sys.exit(0 if result.is_success else 1)


@build.command(help="The status of the current local branch from MPyL's perspective")
@click.pass_obj
def status(obj: CliContext):
    upgrade_check = None
    try:
        upgrade_check = asyncio.wait_for(warn_if_update(obj.console), timeout=3)
        __print_status(obj)
    except asyncio.exceptions.TimeoutError:
        pass
    finally:
        if upgrade_check:
            asyncio.get_event_loop().run_until_complete(upgrade_check)


def __print_status(obj: CliContext):
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    console = obj.console
    console.print(f"MPyL log level is set to {run_properties.console.log_level}")

    branch = obj.repo.get_branch
    main_branch = obj.repo.main_branch
    tag = run_properties.versioning.tag

    if tag is None:
        if run_properties.versioning.branch and not obj.repo.get_branch:
            console.print("Current branch is detached.")
        else:
            console.log(
                Markdown(
                    f"Branch not specified at `build.versioning.branch` in _{DEFAULT_RUN_PROPERTIES_FILE_NAME}_, "
                    f"falling back to git: _{obj.repo.get_branch}_"
                )
            )

        if branch == main_branch:
            console.log(f"On main branch ({branch}), cannot determine build status")
            return

    version = run_properties.versioning
    revision = version.revision or obj.repo.get_sha
    base_revision = obj.repo.base_revision
    if tag:
        console.print(Markdown(f"**Tag:** `{version.tag}` at `{revision}`. "))
    else:
        base_revision_specification = (
            f"at `{base_revision}`"
            if base_revision
            else f"not present. Earliest revision: `{obj.repo.root_commit_hex}` (grafted)."
        )
        console.print(
            Markdown(f"**Branch:** `{branch}`. Base {base_revision_specification}. ")
        )

    result = get_build_plan(
        logger=logging.getLogger("mpyl"),
        repo=obj.repo,
        run_properties=run_properties,
        cli_parameters=MpylCliParameters(local=sys.stdout.isatty()),
    )
    if result.run_plan:
        console.print(
            Markdown("**Execution plan:**  \n" + execution_plan_as_markdown(result))
        )
    else:
        console.print("No changes detected, nothing to do.")


class Pipeline(ParamType):
    name = "pipeline"

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        config: dict = parse_config_from_supplied_location(ctx, param)

        pipelines: dict[str, str] = config["jenkins"]["pipelines"]

        return [
            CompletionItem(value=pl[0], help=pl[1])
            for pl in pipelines.items()
            if incomplete in pl[0]
        ]


def select_tag(ctx) -> str:
    console = Console()
    with console.status("Fetching tags...") as spinner:
        github_config = GithubConfig.from_config(ctx.obj.config)
        github = Github(login_or_token=get_token(github_config))

        repo = github.get_repo(github_config.repository)

        def to_choice(git_release: GitRelease):
            title = (
                git_release.title
                + " "
                + git_release.body.split("* ")[-1].splitlines()[0]
            )
            return Choice(title=title, value=git_release.title)

        choices = map(to_choice, repo.get_releases())
        user_name = github.get_user().login

        def by_choice(choice: Choice):
            # prioritize own tags
            if user_name in str(choice.title):
                return f"9{choice.value}"
            return choice.value

        sorted_choices = sorted(choices, key=by_choice, reverse=True)

        spinner.stop()
        release_id = questionary.select(
            "Which tag do you want to release?",
            show_selected=True,
            choices=sorted_choices,
        ).ask()
        release = repo.get_release(release_id)
        return release.tag_name


def select_target():
    return questionary.select(
        "Which environment do you want to deploy to?",
        show_selected=True,
        choices=[
            Choice(title=t.name, value=t.name)  # pylint: disable=no-member
            for t in [Target.ACCEPTANCE, Target.PULL_REQUEST_BASE, Target.PRODUCTION]
        ],
    ).ask()


def ask_for_tag_input(ctx, _param, value) -> Optional[str]:
    if value == "not_set":
        return None
    if value == "prompt":
        return select_tag(ctx)
    return value


@build.command(help="Run a multi branch pipeline build on Jenkins")
@click.option(
    "--user",
    "-u",
    help="Authentication API user. Can be set via env var JENKINS_USER",
    envvar="JENKINS_USER",
    type=click.STRING,
    required=True,
)
@click.option(
    "--password",
    "-p",
    help="Authentication API password. Can be set via env var JENKINS_PASSWORD",
    envvar="JENKINS_PASSWORD",
    type=click.STRING,
    required=True,
)
@click.option(
    "--pipeline",
    "-pl",
    help="The pipeline to run. Must be one of the pipelines listed in `jenkins.pipelines`. "
    "Default value is `jenkins.defaultPipeline`",
    type=Pipeline(),
    required=False,
)
@click.option(
    "--version",
    "-v",
    help="A specific version on https://pypi.org/project/mpyl/ to use for the build.",
    type=click.STRING,
    required=False,
)
@click.option(
    "--test",
    "-t",
    help="The version supplied by `--version` should be considered from the Test PyPi mirror at"
    " https://test.pypi.org/project/mpyl/.",
    is_flag=True,
    default=False,
    required=False,
)
@click.option(
    "--arguments",
    "-a",
    multiple=True,
    help="A series of arguments to pass to the pipeline. Note that will run within the pipenv in jenkins. "
    "To execute `mpyl build status`, pass `-a run -a mpyl -a build -a status`",
)
@click.option(
    "--background",
    "-bg",
    help="Starts Jenkins build in a 'fire and forget' fashion. "
    "Can be set via env var MPYL_JENKINS_BACKGROUND",
    envvar="MPYL_JENKINS_BACKGROUND",
    is_flag=True,
    default=False,
)
@click.option(
    "--silent",
    "-s",
    help="Indicates whether to show Jenkins' logging or not. "
    "Can be set via env var MPYL_JENKINS_SILENT",
    envvar="MPYL_JENKINS_SILENT",
    is_flag=True,
    default=False,
)
@click.option(
    "--tag",
    is_flag=False,
    flag_value="prompt",
    default="not_set",
    callback=ask_for_tag_input,
)
@click.pass_context
def jenkins(  # pylint: disable=too-many-arguments
    ctx,
    user,
    password,
    pipeline,
    version,
    test,
    arguments,
    background,
    silent,
    tag,
):
    upgrade_check = None
    try:
        upgrade_check = asyncio.wait_for(warn_if_update(ctx.obj.console), timeout=5)
        if "jenkins" not in ctx.obj.config:
            ctx.obj.console.print(
                "No Jenkins configuration found in config file. "
                "Please add a `jenkins` section to your MPyL config file."
            )
            sys.exit(0)
        jenkins_config = ctx.obj.config["jenkins"]

        selected_pipeline = pipeline if pipeline else jenkins_config["defaultPipeline"]
        pipeline_parameters = (
            {"TEST": "true" if test else "false", "VERSION": version} if version else {}
        )
        if arguments:
            pipeline_parameters["BUILD_PARAMS"] = " ".join(arguments)

        run_argument = JenkinsRunParameters(
            jenkins_user=user,
            jenkins_password=password,
            config=ctx.obj.config,
            pipeline=selected_pipeline,
            pipeline_parameters=pipeline_parameters,
            verbose=not silent or ctx.obj.verbose,
            follow=not background,
            tag=tag,
            tag_target=getattr(Target, select_target()) if tag else None,
        )

        run_jenkins(run_argument)
    except asyncio.exceptions.TimeoutError:
        pass
    finally:
        if upgrade_check:
            asyncio.get_event_loop().run_until_complete(upgrade_check)


@build.command(help=f"Clean MPyL metadata in `{BUILD_ARTIFACTS_FOLDER}` folders")
@click.option(
    "--filter",
    "-f",
    "filter_",
    required=False,
    type=click.STRING,
    help="Filter based on filepath ",
)
@click.pass_obj
def clean(obj: CliContext, filter_):
    found_projects: list[Path] = [
        Path(
            load_project(
                obj.repo.root_dir, Path(project_path), strict=False
            ).target_path
        )
        for project_path in obj.repo.find_projects(filter_ if filter_ else "")
    ]

    paths_to_clean = [path for path in found_projects if path.exists()]
    if paths_to_clean:
        for target_path in paths_to_clean:
            shutil.rmtree(target_path)
            obj.console.print(f"🧹 Cleaned up {target_path}")
    else:
        obj.console.print("Nothing to clean")


if __name__ == "__main__":
    build()  # pylint: disable=no-value-for-parameter
