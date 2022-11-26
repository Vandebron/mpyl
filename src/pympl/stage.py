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
