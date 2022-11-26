from dataclasses import dataclass

from ..project import Project
from ..stage import Stage


@dataclass(frozen=True)
class Input:
    project: Project


@dataclass(frozen=True)
class Output:
    success: bool
    message: str


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    version: str
    stage: Stage

    def __str__(self) -> str:
        return f'{self.name}: {self.version}'
