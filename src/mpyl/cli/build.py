"""Commands related to build"""

import asyncio
import pickle
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional, cast, Sequence

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
    MpylCliParameters,
)
from . import create_console_logger
from .commands.build.artifacts import prepare_artifacts_repo, branch_name
from ..artifacts.build_artifacts import (
    ManifestPathTransformer,
    BuildCacheTransformer,
    ArtifactType,
)
from ..build import print_status, run_mpyl
from ..constants import (
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_RUN_PROPERTIES_FILE_NAME,
    RUN_ARTIFACTS_FOLDER,
    RUN_RESULT_FILE_GLOB,
)
from ..project import load_project, Target
from ..run_plan import RunPlan
from ..steps.deploy.k8s.deploy_config import DeployConfig
from ..steps.models import RunProperties
from ..steps.run_properties import construct_run_properties
from ..utilities.github import GithubConfig, get_token
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
    console_config = construct_run_properties(
        properties=parsed_properties,
        config=parsed_config,
        run_plan=RunPlan.empty(),
        all_projects=set(),
    ).console
    console = create_console_logger(
        show_path=console_config.show_paths,
        verbose=verbose,
        max_width=console_config.width,
    )

    repo = ctx.with_resource(Repository(config=RepoConfig.from_config(parsed_config)))
    ctx.obj = CliContext(parsed_config, repo, console, verbose, parsed_properties)


class CustomValidation(click.Command):
    def invoke(self, ctx):
        selected_stage = ctx.params.get("stage")
        stages = [stage["name"] for stage in ctx.obj.run_properties["stages"]]

        if selected_stage and selected_stage not in stages:
            raise click.ClickException(
                message=f"Stage {ctx.params.get('stage')} is not defined in the configuration."
            )

        super().invoke(ctx)


@build.command(help="Run an MPyL build", cls=CustomValidation)
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
@click.option(
    "--stage",
    default=None,
    type=str,
    required=False,
    help="Stage to run",
)
@click.option(
    "--sequential",
    is_flag=True,
    default=False,
    required=False,
    help="Combine results with previous run(s) and load existing run plan",
)
@click.option(
    "--projects",
    "-p",
    type=str,
    required=False,
    help="Comma separated list of the projects to build",
)
@click.option(
    "--dryrun",
    "dryrun_",
    is_flag=True,
    default=False,
    help="don't push or deploy images",
)
@click.pass_obj
def run(
    obj: CliContext,
    ci,
    all_,
    tag,
    stage,
    sequential,
    projects,
    dryrun_,
):  # pylint: disable=invalid-name
    run_result_files = list(Path(RUN_ARTIFACTS_FOLDER).glob(RUN_RESULT_FILE_GLOB))
    if not sequential:
        for run_result_file in run_result_files:
            run_result_file.unlink()

    asyncio.run(warn_if_update(obj.console))

    parameters = MpylCliParameters(
        local=not ci,
        pull_main=all_,
        all=all_,
        verbose=obj.verbose,
        tag=tag,
        stage=stage,
        projects=projects,
        dryrun=dryrun_,
    )
    obj.console.log(parameters)

    run_properties = construct_run_properties(
        config=obj.config,
        properties=obj.run_properties,
        cli_parameters=parameters,
    )
    run_result = run_mpyl(
        run_properties=run_properties, cli_parameters=parameters, reporter=None
    )

    Path(RUN_ARTIFACTS_FOLDER).mkdir(parents=True, exist_ok=True)
    run_result_file = Path(RUN_ARTIFACTS_FOLDER) / f"run_result-{uuid.uuid4()}.pickle"
    with open(run_result_file, "wb") as file:
        pickle.dump(run_result, file, pickle.HIGHEST_PROTOCOL)

    sys.exit(0 if run_result.is_success else 1)


@build.command(help="The status of the current local branch from MPyL's perspective")
@click.option(
    "--all",
    "all_",
    is_flag=True,
    help="Build all projects, regardless of changes on branch",
)
@click.option(
    "--projects",
    "-p",
    type=str,
    required=False,
    help="Comma separated list of the projects to build",
)
@click.option(
    "--stage",
    default=None,
    type=str,
    required=False,
    help="Stage to get status for",
)
@click.option("--tag", "-t", help="Tag to build", type=click.STRING, required=False)
@click.option("--explain", "-e", is_flag=True, help="Explain the current run plan")
@click.pass_obj
def status(obj: CliContext, all_, projects, stage, tag, explain):
    upgrade_check = None
    try:
        upgrade_check = asyncio.wait_for(warn_if_update(obj.console), timeout=3)
        parameters = MpylCliParameters(
            local=sys.stdout.isatty(), all=all_, projects=projects, stage=stage, tag=tag
        )
        print_status(obj, parameters, explain)
    except asyncio.exceptions.TimeoutError:
        pass
    finally:
        if upgrade_check:
            asyncio.get_event_loop().run_until_complete(upgrade_check)


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


def select_targets() -> list[str]:
    return questionary.checkbox(
        "Which environment do you want to deploy to?",
        choices=[
            Choice(title=t.name, value=t.name)  # pylint: disable=no-member
            for t in [Target.PULL_REQUEST_BASE, Target.ACCEPTANCE, Target.PRODUCTION]
        ],
    ).ask()


def ask_for_tag_input(ctx, _param, value) -> Optional[str]:
    if value == "not_set":
        return None
    if value == "prompt":
        return select_tag(ctx)
    return value


@build.command(help=f"Clean all MPyL metadata in `{RUN_ARTIFACTS_FOLDER}` folders")
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
    root_path = Path(RUN_ARTIFACTS_FOLDER)
    if root_path.is_dir():
        shutil.rmtree(root_path)
        obj.console.print(f"🧹 Cleaned up {root_path}")

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
        for target_path in set(paths_to_clean):
            shutil.rmtree(target_path)
            obj.console.print(f"🧹 Cleaned up {target_path}")
    else:
        obj.console.print("Nothing to clean")


@build.group(
    "artifacts",
    help="Commands related to artifacts like build cache and k8s manifests",
)
def artifacts():  # no implementation, only for nesting command
    pass


@artifacts.command(help="Pull build artifacts from remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option("--pr", type=click.INT, help="PR number to fetch", required=False)
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=False),
    help="Path within repository to copy artifacts from",
    default=Path("tmp"),
    required=False,
)
@click.pass_obj
def pull(obj: CliContext, tag: str, pr: int, path: Path):
    run_properties = construct_run_properties(
        config=obj.config,
        properties=obj.run_properties,
        run_plan=RunPlan.empty(),
        all_projects=set(),
    )
    target_branch = __get_target_branch(run_properties, tag, pr)

    build_artifacts = prepare_artifacts_repo(
        obj=obj, repo_path=path, artifact_type=ArtifactType.CACHE
    )
    build_artifacts.pull(
        branch=branch_name(
            identifier=target_branch,
            artifact_type=ArtifactType.CACHE,
            target=run_properties.target,
        )
    )


@artifacts.command(help="Push build artifacts to remote artifact repository")
@click.option("--tag", "-t", type=click.STRING, help="Tag to build", required=False)
@click.option("--pr", type=click.INT, help="PR number to fetch", required=False)
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=False),
    help="Path within repository to copy artifacts to",
    required=False,
)
@click.option(
    "--artifact-type",
    "-a",
    type=click.Choice(
        cast(Sequence[str], ArtifactType)
    ),  # Click does accept this enum type but mypy doesn't
    help="The type of artifact to store. Either build metadata from `.mpyl` "
    "folders or k8s manifests to be deployed by ArgoCD",
    required=True,
)
@click.pass_obj
def push(
    obj: CliContext,
    tag: Optional[str],
    pr: Optional[int],
    path: Path,
    artifact_type: ArtifactType,
):
    run_properties = construct_run_properties(
        config=obj.config,
        properties=obj.run_properties,
        run_plan=RunPlan.empty(),
        all_projects=set(),
    )
    target_branch = __get_target_branch(run_properties, tag, pr)
    if path is None:
        path = Path("tmp") if artifact_type == ArtifactType.CACHE else Path(".")

    build_artifacts = prepare_artifacts_repo(
        obj=obj, repo_path=path, artifact_type=artifact_type
    )
    deploy_config = DeployConfig.from_config(obj.config)

    transformer = (
        ManifestPathTransformer(
            deploy_config=deploy_config, run_properties=run_properties
        )
        if artifact_type == ArtifactType.ARGO
        else BuildCacheTransformer()
    )

    github_config = None
    if artifact_type == ArtifactType.ARGO:
        github = obj.config["vcs"]["argoGithub"]
        github_config = GithubConfig.from_github_config(github=github)

    build_artifacts.push(
        branch=branch_name(
            identifier=target_branch,
            artifact_type=artifact_type,
            target=run_properties.target,
        ),
        revision=obj.repo.get_sha,
        repository_url=obj.repo.remote_url if obj.repo.remote_url else "",
        project_paths=obj.repo.find_projects(),
        path_transformer=transformer,
        run_properties=run_properties,
        github_config=github_config,
    )


def __get_target_branch(
    run_properties: RunProperties, tag: Optional[str], pr: Optional[int]
) -> str:
    effective_tag = tag or run_properties.versioning.tag
    effective_pr = pr or run_properties.versioning.pr_number
    if effective_tag is None and effective_pr is None:
        raise click.ClickException(
            "Either pr or tag must be specified, either as a flag or in the run properties"
        )

    if effective_tag:
        return effective_tag

    return f"PR-{effective_pr}"


if __name__ == "__main__":
    build()  # pylint: disable=no-value-for-parameter
