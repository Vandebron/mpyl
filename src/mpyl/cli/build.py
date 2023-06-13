"""Commands related to build"""
import asyncio
import shutil
from pathlib import Path
from typing import Optional

import click
import questionary
from click import ParamType, BadParameter
from click.shell_completion import CompletionItem
from github import Github
from github.GitRelease import GitRelease
from questionary import Choice
from rich.console import Console
from rich.markdown import Markdown

from . import CliContext, CONFIG_PATH_HELP, check_updates, get_meta_version
from . import create_console_logger
from .commands.build.jenkins import JenkinsRunParameters, run_jenkins, get_token
from .commands.build.mpyl import MpylRunParameters, run_mpyl, MpylCliParameters, MpylRunConfig, find_build_set
from ..constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME, BUILD_ARTIFACTS_FOLDER
from ..project import load_project, Target
from ..reporting.formatting.markdown import run_result_to_markdown
from ..steps.models import RunProperties
from ..steps.run import RunResult
from ..utilities.github import GithubConfig
from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository, RepoConfig


async def warn_if_update(console: Console):
    version = get_meta_version()
    update = await check_updates(meta=version)
    if update:
        console.print(Markdown(f"⚠️  **You can upgrade from {version} to {update} :** `pip install -U mpyl=={update}`"))


@click.group('build')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help=CONFIG_PATH_HELP,
              envvar="MPYL_CONFIG_PATH", default=DEFAULT_CONFIG_FILE_NAME)
@click.option('--properties', '-p', required=False, type=click.Path(exists=False), help='Path to run properties',
              envvar="MPYL_RUN_PROPERTIES_PATH", default=DEFAULT_RUN_PROPERTIES_FILE_NAME, show_default=True)
@click.option('--verbose', '-v', is_flag=True, default=False, show_default=True, help='Verbose output')
@click.pass_context
def build(ctx, config, properties, verbose):
    """Pipeline build commands"""
    console = create_console_logger(local=False, verbose=verbose)
    parsed_config = parse_config(config)
    parsed_properties = parse_config(properties)

    repo = ctx.with_resource(Repository(config=RepoConfig.from_config(parsed_config)))
    ctx.obj = CliContext(parsed_config, repo, console, verbose, parsed_properties)


@build.command(help='Run an MPyL build')
@click.option('--ci', is_flag=True,
              help='Run as CI build instead of local. Ignores unversioned changes.')
@click.option('--all', 'all_', is_flag=True, help='Build all projects, regardless of changes on branch')
@click.option(
    '--tag', '-t',
    help='Tag to build',
    type=click.STRING,
    required=False
)
@click.pass_obj
def run(obj: CliContext, ci, all_, tag):  # pylint: disable=invalid-name
    asyncio.run(warn_if_update(obj.console))
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config) if ci \
        else RunProperties.for_local_run(obj.config, obj.repo.get_sha, obj.repo.get_branch, tag)

    parameters = MpylCliParameters(local=not ci, pull_main=all_, all=all_, verbose=obj.verbose, tag=tag)
    obj.console.log(parameters)
    run_parameters = MpylRunParameters(
        run_config=MpylRunConfig(config=obj.config, run_properties=run_properties),
        parameters=parameters
    )
    run_mpyl(run_parameters, None)


@build.command(help="The status of the current local branch from MPyL's perspective")
@click.pass_obj
def status(obj: CliContext):
    try:
        upgrade_check = asyncio.wait_for(warn_if_update(obj.console), timeout=3)
        __print_status(obj)
        asyncio.get_event_loop().run_until_complete(upgrade_check)
    except asyncio.exceptions.TimeoutError:
        pass


def __print_status(obj: CliContext):
    run_properties = RunProperties.from_configuration(obj.run_properties, obj.config)
    branch = run_properties.versioning.branch
    if not branch:
        branch = obj.repo.get_branch
        obj.console.log(
            f'Branch not specified in `{DEFAULT_RUN_PROPERTIES_FILE_NAME}`. Branch determined via git: {branch}')

    if branch and obj.repo.main_branch == obj.repo.get_branch:
        obj.console.log(f'On main branch ({branch}), cannot determine build status')
        return
    tag = obj.repo.get_tag if not branch else None
    version = run_properties.versioning
    revision = "Tag" if tag else "Branch"
    obj.console.print(Markdown(f"**{revision}:** `{version.branch or version.tag}` at `{version.revision}`"))

    if obj.repo.main_branch_pulled:
        changes = obj.repo.changes_in_branch_including_local() if branch else obj.repo.changes_in_merge_commit()
        build_set = find_build_set(obj.repo, changes, False)
        result = RunResult(run_properties=run_properties, run_plan=build_set)
        if result.run_plan:
            obj.console.print(Markdown("**Execution plan:**  \n" + run_result_to_markdown(result)))
        else:
            obj.console.print("No changes detected, nothing to do.")


class Pipeline(ParamType):
    name = 'pipeline'

    def shell_complete(self, ctx: click.Context, param, incomplete: str):
        if not ctx.parent or ctx.parent.params['config'] is None or not Path(ctx.parent.params['config']).exists():
            raise BadParameter('Either --config parameter must or MPYL_CONFIG_PATH env var must be set', ctx=ctx,
                               param=param)

        config: dict = parse_config(ctx.parent.params['config'])
        parsed_config: dict[str, str] = config['jenkins']['pipelines']

        return [
            CompletionItem(value=pl[0], help=pl[1]) for pl in parsed_config.items() if
            incomplete in pl[0]
        ]


def select_tag(ctx) -> str:
    console = Console()
    with console.status("Fetching tags...") as spinner:
        github_config = GithubConfig.from_config(ctx.obj.config)
        github = Github(login_or_token=get_token(github_config))

        repo = github.get_repo(github_config.repository)

        def to_choice(git_release: GitRelease):
            title = git_release.title + " " + git_release.body.split('* ')[-1].splitlines()[0]
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
        release_id = questionary.select("Which tag do you want to release?", show_selected=True,
                                        choices=sorted_choices).ask()
        release = repo.get_release(release_id)
        return release.tag_name


def ask_for_input(ctx, _param, value) -> Optional[str]:
    if value == "not_set":
        return None
    if value == "prompt":
        return select_tag(ctx)
    return value


@build.command(help='Run a multi branch pipeline build on Jenkins')
@click.option(
    '--user', '-u',
    help='Authentication API user. Can be set via env var JENKINS_USER',
    envvar="JENKINS_USER",
    type=click.STRING,
    required=True
)
@click.option(
    '--password', '-p',
    help='Authentication API password. Can be set via env var JENKINS_PASSWORD',
    envvar="JENKINS_PASSWORD",
    type=click.STRING,
    required=True
)
@click.option(
    '--pipeline', '-pl',
    help='The pipeline to run. Must be one of the pipelines listed in `jenkins.pipelines`. '
         'Default value is `jenkins.defaultPipeline`',
    type=Pipeline(),
    required=False
)
@click.option(
    '--test', '-t',
    help='A specific test version on https://test.pypi.org/project/mpyl/ to use for the build.',
    type=click.STRING,
    required=False
)
@click.option(
    '--version', '-v',
    help='A specific stable version on https://pypi.org/project/mpyl/ to use for the build. Default is the current.',
    type=click.STRING,
    required=False
)
@click.option(
    '--target', '-tg',
    help='The deploy target for a --tag build',
    type=click.Choice([Target.ACCEPTANCE.value, Target.PRODUCTION.value]),
    required=True
)
@click.option(
    '--arguments', '-a',
    multiple=True,
    help='A series of arguments to pass to the pipeline. Note that will run within the pipenv in jenkins. '
         'To execute `mpyl build status`, pass `-a run -a mpyl -a build -a status`',
)
@click.option(
    '--background', '-bg',
    help="Starts Jenkins build in a 'fire and forget' fashion. "
         "Can be set via env var MPYL_JENKINS_BACKGROUND",
    envvar="MPYL_JENKINS_BACKGROUND",
    is_flag=True,
    default=False
)
@click.option(
    '--silent', '-s',
    help="Indicates whether to show Jenkins' logging or not. "
         "Can be set via env var MPYL_JENKINS_SILENT",
    envvar="MPYL_JENKINS_SILENT",
    is_flag=True,
    default=False
)
@click.option('--tag', '-tg', is_flag=False, flag_value="prompt", default="not_set", callback=ask_for_input)
@click.pass_context
def jenkins(ctx, user, password, pipeline, test, version, target, arguments, background, silent,  # pylint: disable=too-many-arguments
            tag):
    try:
        if test and version:
            raise click.BadArgumentUsage('Cannot specify both --test and --version')
        if not version and not tag:
            version = get_meta_version()
        if tag and not target:
            raise click.BadArgumentUsage('--target must be specified when using --tag')

        upgrade_check = asyncio.wait_for(warn_if_update(ctx.obj.console), timeout=5)
        selected_pipeline = pipeline if pipeline else ctx.obj.config['jenkins']['defaultPipeline']

        pipeline_parameters = {}
        if arguments:
            pipeline_parameters['PIPENV_PARAMS'] = " ".join(arguments)
        if target:
            pipeline_parameters['DEPLOY_TARGET'] = target
        if test:
            pipeline_parameters['TEST_VERSION'] = test
            pipeline_parameters['TEST'] = 'true'
        elif version:
            pipeline_parameters['VERSION'] = version

        run_argument = JenkinsRunParameters(
            jenkins_user=user, jenkins_password=password, config=ctx.obj.config,
            pipeline=selected_pipeline, pipeline_parameters=pipeline_parameters,
            verbose=not silent or ctx.obj.verbose,
            follow=not background, tag=tag
        )

        run_jenkins(run_argument)
        asyncio.get_event_loop().run_until_complete(upgrade_check)
    except asyncio.exceptions.TimeoutError:
        pass


@build.command(help=f'Clean MPyL metadata in `{BUILD_ARTIFACTS_FOLDER}` folders')
@click.option('--filter', '-f', 'filter_', required=False, type=click.STRING, help='Filter based on filepath ')
@click.pass_obj
def clean(obj: CliContext, filter_):
    found_projects: list[Path] = [
        Path(load_project(obj.repo.root_dir(), Path(project_path), strict=False).target_path)
        for project_path in obj.repo.find_projects(filter_ if filter_ else '')
    ]

    paths_to_clean = [path for path in found_projects if path.exists()]
    if paths_to_clean:
        for target_path in paths_to_clean:
            shutil.rmtree(target_path)
            obj.console.print(f"🧹 Cleaned up {target_path}")
    else:
        obj.console.print("Nothing to clean")


if __name__ == '__main__':
    build()  # pylint: disable=no-value-for-parameter
