"""
.. include:: ../../README.md
"""
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Stage(Enum):
    def __eq__(self, other):
        return self.value == other.value

    BUILD = 'build'
    TEST = 'test'
    DEPLOY = 'deploy'
    POST_DEPLOY = 'postdeploy'


@dataclass(frozen=True)
class Target(Enum):
    def __eq__(self, other):
        return self.value == other.value

    PULL_REQUEST = 'PullRequest'
    PULL_REQUEST_BASE = 'PullRequestBase'
    ACCEPTANCE = 'Acceptance'
    PRODUCTION = 'Production'
