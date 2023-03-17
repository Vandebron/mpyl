"""Github related utility methods"""
from dataclasses import dataclass
from typing import Dict, Optional

from github.PullRequest import PullRequest
from github.Repository import Repository


@dataclass
class GithubAppConfig:
    private_app_key_path: Optional[str]
    private_key_base_64_encoded: Optional[str]
    app_key: str

    def __init__(self, config: Dict):
        self.private_app_key_path = config.get('privateKeyPath')
        self.private_key_base_64_encoded = config.get('privateKeyBase64Encoded')
        if not self.private_key_base_64_encoded and not self.private_app_key_path:
            raise KeyError("When github.app is configured, either 'privateKeyPath' "
                           "or 'privateKeyBase64Encoded' need to be defined")

        self.app_key = config['appId']


@dataclass
class GithubConfig:
    repository: str
    owner: str
    repo_name: str
    token: str
    app_config: dict

    def __init__(self, config: Dict):
        github = config['cvs']['github']
        self.repository = github['repository']
        parts = self.repository.split('/')
        self.owner = parts[0]
        self.repo_name = parts[1]
        self.token = github['token']
        self.app_config = github.get('app', {})

    @property
    def get_app_config(self) -> GithubAppConfig:
        return GithubAppConfig(self.app_config)


def get_pr_for_branch(repo: Repository, branch: str) -> PullRequest:
    pulls = repo.get_pulls(head=f'{repo.full_name}:{branch}').get_page(0)

    if len(pulls) == 0:
        raise ValueError(f'No PR related to {branch} was found. Did create it yet? `gh pr create --draft`')

    return pulls.pop()
