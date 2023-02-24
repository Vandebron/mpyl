"""
# Github reporter

## PR comment
Pipeline results can be reported in the form of a user comment on the pull request, using the `PullRequestComment`
 reporter.
You are recommended to use a bot account as the authenticated user.

### Installation instructions
 1. Go to your bot user's personal Github profile settings
 2. Under *Developer Settings* -> *Personal access tokens* -> *Fine grained tokens*, click **Generate new token**
 3. Enable `Read` / `Write` access for *Pull requests*
 4. Make sure that this token is present as `GITHUB_TOKEN` env var in your pipeline's runner.

## Checks

The `CommitCheck` reporter reports your build pipeline's result in the form of a
[check](https://docs.github.com/en/rest/checks).
![Pull request check](documentation_images/pr-check.png)

Checks can be referred to from branch protection rules, in order to prevent faulty code from being merged.

### Installation instructions

 1. Install the [https://github.com/apps/mpyl-pipeline](https://github.com/apps/mpyl-pipeline)
 Github app to your repository.
 2. Go to your repository's *Setting* -> *Integrations* -> *Github Apps* and click **Configure** for*_MPyL Pipeline*
 3. In the app's settings page, scroll down and click **Generate a private key**
 4. The private key needs to be made available at the location configured in `csv.targets.app.privateKeyPath` at
  runtime.

"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from github import Github, GithubIntegration
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository as GithubRepository

from . import Reporter
from ..markdown import run_result_to_markdown
from ..simple import to_string
from ...steps.models import RunProperties
from ...steps.run import RunResult
from ...utilities.repo import Repository, RepoConfig


@dataclass
class GithubAppConfig:
    private_app_key_path: str
    app_key: str

    def __init__(self, config: Dict):
        self.private_app_key_path = config['privateKeyPath']
        self.app_key = config['appId']


@dataclass
class GithubConfig:
    repository: str
    owner: str
    repo_name: str
    token: str
    app_config: Optional[GithubAppConfig] = None

    def __init__(self, config: Dict):
        github = config['cvs']['github']
        self.repository = github['repository']
        parts = self.repository.split('/')
        self.owner = parts[0]
        self.repo_name = parts[1]
        self.token = github['token']

        app_config = github.get('app', {})
        if app_config:
            self.app_config = GithubAppConfig(app_config)


class PullRequestComment(Reporter):
    _config: GithubConfig

    def __init__(self, config: Dict):
        self._config = GithubConfig(config)
        self.git_repository = Repository(RepoConfig(config))

    def _get_pull_request(self, repo: GithubRepository, run_properties: RunProperties):
        if run_properties.versioning.pr_number:
            return repo.get_pull(run_properties.versioning.pr_number)

        current_branch = self.git_repository.get_branch
        pulls: list[PullRequest] = repo.get_pulls(head=f'{repo.full_name}:{current_branch}').get_page(0)

        if len(pulls) == 0:
            raise ValueError(f'No PR related to {current_branch} were found')

        return pulls.pop()

    def send_report(self, results: RunResult) -> None:
        github = Github(self._config.token)
        repo = github.get_repo(self._config.repository)

        pull_request = self._get_pull_request(repo, results.run_properties)

        comments = pull_request.get_issue_comments()
        authenticated_user = github.get_user()
        comments_for_user = [c for c in comments if c.user.id == authenticated_user.id]
        if comments_for_user:
            comment_to_update: IssueComment = comments_for_user.pop()
            comment_to_update.edit(run_result_to_markdown(results))
        else:
            pull_request.create_issue_comment(run_result_to_markdown(results))


class CommitCheck(Reporter):
    _config: GithubConfig
    _check_run_id: Optional[int]

    def __init__(self, config: Dict):
        self._config = GithubConfig(config)
        self.git_repository = Repository(RepoConfig(config))
        self._check_run_id = None

    @staticmethod
    def _to_output(results: RunResult) -> dict:
        build_id = results.run_properties.build_id
        summary = ':white_check_mark: Build successful' if results.is_success else ':x: Build failed'
        return {'title': f'Build {build_id}', 'summary': summary + '\n' + run_result_to_markdown(results),
                'text': to_string(results)}

    def send_report(self, results: RunResult) -> None:
        config = self._config.app_config
        if not config:
            raise ValueError("github.app config needs to be defined")

        private_key = Path(config.private_app_key_path).read_text(encoding='utf-8')
        integration = GithubIntegration(integration_id=config.app_key, private_key=private_key)

        install = integration.get_installation(self._config.owner, self._config.repo_name)
        access_token = integration.get_access_token(install.id)
        github = Github(login_or_token=access_token.token)
        repo = github.get_repo(self._config.repository)
        if self._check_run_id:
            run = repo.get_check_run(self._check_run_id)
            run.edit(completed_at=datetime.now(), conclusion='success', output=self._to_output(results))
        else:
            self._check_run_id = repo.create_check_run(name='Pipeline build', head_sha=self.git_repository.get_sha,
                                                       status='in_progress').id
