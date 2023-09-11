"""Jenkins multibranch pipeline build tool"""
import subprocess
from dataclasses import dataclass
from typing import Optional

import requests
from github import Github
from jenkinsapi.jenkins import Jenkins
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status

from . import play_sound, Sound
from ....project import Target
from ....utilities.github import GithubConfig, get_pr_for_branch
from ....utilities.jenkins import JenkinsConfig, Pipeline
from ....utilities.jenkins.runner import JenkinsRunner
from ....utilities.repo import RepoConfig, Repository


@dataclass(frozen=True)
class JenkinsRunParameters:
    jenkins_user: str
    jenkins_password: str
    config: dict
    pipeline: str
    pipeline_parameters: dict
    verbose: bool
    follow: bool
    tag: Optional[str] = None
    tag_target: Target = Target.ACCEPTANCE


def get_token(github_config: GithubConfig):
    if github_config.token:
        return github_config.token
    return (
        subprocess.run(
            ["gh", "auth", "token"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )


def __get_pr_pipeline(
    config: dict, git_repo: Repository, pipeline: str, status: Status
) -> Optional[Pipeline]:
    github_config = GithubConfig.from_config(config)
    github = Github(login_or_token=get_token(github_config))

    repo = github.get_repo(github_config.repository)

    branch = git_repo.get_branch
    if not branch:
        status.console.log("Could not determine current branch")
        return None

    if git_repo.main_branch == branch:
        status.console.log(
            f"On main branch ({branch}), cannot determine which PR to build"
        )
        return None
    try:
        pull = get_pr_for_branch(repo, branch)
        return Pipeline(
            target=Target.PULL_REQUEST,
            tag=f"{pull.number}",
            url=pull.html_url,
            pipeline=pipeline,
            body=pull.body,
            jenkins_config=JenkinsConfig.from_config(config),
        )
    except ValueError as exc:
        status.console.log(exc)
        return None


def run_jenkins(run_config: JenkinsRunParameters):
    log_console = Console(log_path=False, log_time=False)
    with log_console.status(
        "Fetching Github info.. [bright_blue]>gh pr view[/bright_blue]"
    ) as status:
        config = run_config.config

        with Repository(RepoConfig.from_config(config)) as git_repo:
            try:
                pipeline_info = (
                    Pipeline(
                        target=run_config.tag_target,
                        tag=run_config.tag,
                        url="https://tag-url",
                        pipeline=run_config.pipeline,
                        body="",
                        jenkins_config=JenkinsConfig.from_config(config),
                    )
                    if run_config.tag
                    else __get_pr_pipeline(
                        config, git_repo, run_config.pipeline, status
                    )
                )
                if not pipeline_info:
                    return

                if run_config.tag:
                    run_config.pipeline_parameters[
                        "DEPLOY_CHOICE"
                    ] = run_config.tag_target.value

                status.start()
                status.update(
                    f"Fetching Jenkins info for {pipeline_info.human_readable()} ..."
                )

                runner = JenkinsRunner(
                    pipeline=pipeline_info,
                    jenkins=Jenkins(
                        baseurl=JenkinsConfig.from_config(config).url,
                        username=run_config.jenkins_user,
                        password=run_config.jenkins_password,
                    ),
                    status=status,
                    follow=run_config.follow,
                    verbose=run_config.verbose,
                )
                runner.run(run_config.pipeline_parameters)
            except requests.ConnectionError:
                play_sound(Sound.FAILURE)
                status.console.log("⚠️ Could not connect. Are you on VPN?")
            except Exception as exc:
                status.console.print(Markdown(f"Unexpected exception: {exc}"))
                if run_config.verbose:
                    status.console.print_exception()
                raise exc
