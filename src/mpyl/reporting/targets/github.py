"""
Report `mpyl.steps.run.RunResult` to Github
"""

from dataclasses import dataclass
from typing import Dict

from github import Github
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest

from .. import Reporter
from ..simple import to_string
from ...repo import Repository, RepoConfig
from ...steps.models import RunProperties
from ...steps.run import RunResult


@dataclass
class GithubConfig:
    repository: str
    token: str

    def __init__(self, config: Dict):
        github = config['cvs']['github']
        self.repository = github['repository']
        self.token = github['token']


class GithubReport(Reporter):
    _config: GithubConfig

    def __init__(self, config: Dict):
        self._config = GithubConfig(config)
        self.git_repository = Repository(RepoConfig(config))

    def _get_pull_request(self, github: Github, run_properties: RunProperties):
        repo = github.get_repo(self._config.repository)
        if run_properties.versioning.pr_number:
            return repo.get_pull(run_properties.versioning.pr_number)

        current_branch = self.git_repository.get_branch
        pulls: list[PullRequest] = repo.get_pulls(head=f'{repo.full_name}:{current_branch}').get_page(0)

        if len(pulls) == 0:
            raise ValueError(f'No PR related to {current_branch} were found')

        return pulls.pop()

    def send_report(self, results: RunResult) -> None:
        github = Github(self._config.token)

        pull_request = self._get_pull_request(github, results.run_properties)

        comments = pull_request.get_issue_comments()
        authenticated_user = github.get_user()
        comments_for_user = [c for c in comments if c.user.id == authenticated_user.id]
        if comments_for_user:
            comment_to_update: IssueComment = comments_for_user.pop()
            comment_to_update.edit(to_string(results))
        else:
            pull_request.create_issue_comment(to_string(results))
