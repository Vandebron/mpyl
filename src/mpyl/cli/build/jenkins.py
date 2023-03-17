"""Jenkins multibranch pipeline build tool"""
from dataclasses import dataclass

import requests
from github import Github
from jenkinsapi.jenkins import Jenkins
from rich.console import Console
from rich.markdown import Markdown

from ...project import Target
from ...utilities.github import GithubConfig, get_pr_for_branch
from ...utilities.jenkins import JenkinsConfig, Pipeline
from ...utilities.jenkins.runner import JenkinsRunner
from ...utilities.repo import RepoConfig
from ...utilities.repo import Repository


@dataclass(frozen=True)
class JenkinsRunParameters:
    jenkins_user: str
    jenkins_password: str
    config: dict
    pipeline: str
    verbose: bool


def run_jenkins(run_config: JenkinsRunParameters):
    log_console = Console(log_path=False, log_time=False)
    with log_console.status('Fetching Github info.. [blue]>gh pr view[/blue]') as status:
        config = run_config.config
        github_config = GithubConfig(config)
        repo_config = RepoConfig(config)
        with Repository(repo_config) as git_repo:
            try:
                github = Github(login_or_token=github_config.token)
                repo = github.get_repo(github_config.repository)

                branch = git_repo.get_branch
                if repo_config.main_branch == branch:
                    status.console.log(f'On main branch ({branch}), cannot determine which PR to build')
                    return

                pull = get_pr_for_branch(repo, branch)

                jenkins_config = JenkinsConfig.from_config(config)
                pipeline_info = Pipeline(target=Target.PULL_REQUEST, tag=f'{pull.number}', url=pull.url,
                                         pipeline=run_config.pipeline, body=pull.body, jenkins_config=jenkins_config)

                status.start()
                status.update(f'Fetching Jenkins info for {pipeline_info.human_readable()} ...')

                runner = JenkinsRunner(pipeline=pipeline_info,
                                       jenkins=Jenkins(jenkins_config.url, username=run_config.jenkins_user,
                                                       password=run_config.jenkins_password), status=status)
                runner.run()
            except requests.ConnectionError:
                status.console.bell()
                status.console.log('⚠️ Could not connect. Are you on VPN?')
            except Exception as exc:
                status.console.print(Markdown(f'Unexpected exception: {exc}'))
                if run_config.verbose:
                    status.console.print_exception()
                raise exc
