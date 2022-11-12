from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Target(Enum):
    def __eq__(self, other):
        return self.value == other.value

    PULL_REQUEST = 1
    PULL_REQUEST_BASE = 2
    ACCEPTANCE = 3
    PRODUCTION = 4
