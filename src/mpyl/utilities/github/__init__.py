"""GitHub related utility methods"""
from dataclasses import dataclass
from typing import Optional

from github.PullRequest import PullRequest
from github.Repository import Repository


@dataclass
class GithubAppConfig:
    private_app_key_path: Optional[str]
    private_key_base_64_encoded: Optional[str]
    app_key: str

    def __init__(self, config: dict):
        self.private_app_key_path = config.get("privateKeyPath")
        self.private_key_base_64_encoded = config.get("privateKeyBase64Encoded")
        if not self.private_key_base_64_encoded and not self.private_app_key_path:
            raise KeyError(
                "When github.app is configured, either 'privateKeyPath' "
                "or 'privateKeyBase64Encoded' need to be defined"
            )

        self.app_key = config["appId"]


@dataclass(frozen=True)
class GithubConfig:
    repository: str
    owner: str
    repo_name: str
    token: str
    app_config: dict

    @staticmethod
    def from_config(config: dict):
        github = config["vcs"]["github"]
        return GithubConfig.from_github_config(github=github)

    @staticmethod
    def from_github_config(github: dict):
        repo_parts = github["repository"].split("/")
        return GithubConfig(
            repository=(github["repository"]),
            owner=repo_parts[0],
            repo_name=repo_parts[1],
            token=github["token"],
            app_config=github.get("app", {}),
        )

    @property
    def get_app_config(self) -> GithubAppConfig:
        return GithubAppConfig(self.app_config)


def get_pr_for_branch(repo: Repository, branch: str) -> PullRequest:
    pull_request = next(
        (pull for pull in repo.get_pulls() if pull.head.ref == branch), None
    )

    if pull_request is None:
        raise ValueError(
            f"No PR related to {branch} was found. Did you create it yet? `gh pr create --draft`"
        )

    return pull_request
