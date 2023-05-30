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
import base64
from datetime import datetime
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import Dict, Optional, Callable

from github import Github, GithubIntegration, GithubException
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository as GithubRepository

from . import Reporter, ReportOutcome
from ...reporting.formatting.markdown import run_result_to_markdown
from ...reporting.formatting.text import to_string
from ...steps.models import RunProperties
from ...steps.run import RunResult
from ...utilities.github import GithubConfig, get_pr_for_branch, GithubAppConfig
from ...utilities.repo import Repository, RepoConfig


def compose_message_body(results: RunResult, _unused_config: Optional[Dict] = None) -> str:
    return run_result_to_markdown(results)


class GithubOutcome(ReportOutcome):
    pass


class GithubUpdateStategy(Enum):
    BODY = 'body'
    COMMENT = 'comment'


class PullRequestReporter(Reporter):
    _config: GithubConfig

    def __init__(self, config: Dict,
                 compose_function: Callable[[RunResult, Optional[Dict]], str] = compose_message_body,
                 update_stategy: GithubUpdateStategy = GithubUpdateStategy.BODY):
        self._raw_config = config
        self._config = GithubConfig.from_config(config)
        self.git_repository = Repository(RepoConfig.from_config(config))
        self.compose_function = compose_function
        self.update_strategy: GithubUpdateStategy = update_stategy

    def _get_pull_request(self, repo: GithubRepository, run_properties: RunProperties) -> Optional[PullRequest]:
        if run_properties.versioning.pr_number:
            return repo.get_pull(run_properties.versioning.pr_number)

        current_branch = self.git_repository.get_branch
        if current_branch:
            return get_pr_for_branch(repo, current_branch)
        return None

    def _update_pr(self) -> Callable[[PullRequest, RunResult], None]:
        if self.update_strategy == GithubUpdateStategy.COMMENT:
            return self._change_pr_comment
        return self._change_pr_body

    def _change_pr_body(self, pull_request: PullRequest, results: RunResult):
        current_body = (pull_request.body.split("----")[0] if pull_request.body else "") + "----"
        pull_request.edit(body=current_body + self.compose_function(results, self._raw_config))

    def _change_pr_comment(self, pull_request: PullRequest, results: RunResult):
        github = Github(self._config.token)
        comments = pull_request.get_issue_comments()
        authenticated_user = github.get_user()
        comments_for_user = [c for c in comments if c.user.id == authenticated_user.id]
        if comments_for_user:
            comment_to_update: IssueComment = comments_for_user.pop()
            comment_to_update.edit(self.compose_function(results, self._raw_config))
        else:
            pull_request.create_issue_comment(self.compose_function(results, self._raw_config))

    def send_report(self, results: RunResult, text: Optional[str] = None) -> GithubOutcome:
        try:
            github = Github(self._config.token)
            repo = github.get_repo(self._config.repository)

            pull_request = self._get_pull_request(repo, results.run_properties)
            if not pull_request:
                return GithubOutcome(success=False, exception=Exception('No pull request found'))

            self._update_pr()(pull_request, results)
            return GithubOutcome(success=True)
        except GithubException as exc:
            return GithubOutcome(success=False, exception=exc)


class CommitCheck(Reporter):
    _github_config: GithubConfig
    _check_run_id: Optional[int]

    def __init__(self, config: Dict, logger: Logger):
        self._config = config
        self._github_config = GithubConfig.from_config(config)
        self._check_run_id = None
        self._logger = logger

    @staticmethod
    def _to_output(results: RunResult) -> dict:
        build_id = results.run_properties.details.build_id
        summary = ':white_check_mark: Build successful' if results.is_success else ':x: Build failed'
        return {'title': f'Build {build_id}', 'summary': summary + '\n' + run_result_to_markdown(results),
                'text': to_string(results)}

    def send_report(self, results: RunResult, text: Optional[str] = None) -> GithubOutcome:
        try:
            config: GithubAppConfig = self._github_config.get_app_config
            if not config:
                raise KeyError("github.app config needs to be defined")

            private_key = Path(config.private_app_key_path or '').read_text(
                encoding='utf-8') if config.private_app_key_path else base64.b64decode(
                config.private_key_base_64_encoded or '').decode('utf-8')

            integration = GithubIntegration(integration_id=config.app_key, private_key=private_key)

            install = integration.get_installation(self._github_config.owner, self._github_config.repo_name)
            access_token = integration.get_access_token(install.id)
            github = Github(login_or_token=access_token.token)
            repo = github.get_repo(self._github_config.repository)
            if self._check_run_id and results:
                run = repo.get_check_run(self._check_run_id)
                conclusion = 'success' if results is None or results.is_success else 'failure'
                self._logger.info(f'Setting check to {conclusion}')
                run.edit(completed_at=datetime.now(), conclusion=conclusion, output=self._to_output(results))
            else:
                with Repository(RepoConfig.from_config(self._config)) as git_repository:
                    self._check_run_id = repo.create_check_run(name='Pipeline build', head_sha=git_repository.get_sha,
                                                               status='in_progress').id
            return GithubOutcome(success=True)
        except GithubException as exc:
            self._logger.warning(f'Unexpected exception: {exc}', exc_info=True)
            return GithubOutcome(success=False, exception=exc)
