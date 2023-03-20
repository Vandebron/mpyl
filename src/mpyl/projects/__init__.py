"""Projects and how they relate to each other"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..project import Project


@dataclass(frozen=True)
class Protocol(Enum):
    UNKNOWN = 1
    REST = 2
    KAFKA = 3


@dataclass(frozen=True)
class Contract:
    type: Protocol
    contract_file: Optional[str]


@dataclass(frozen=True)
class Dependency:
    project: Project
    contracts: set[Contract]


@dataclass
class ProjectWithDependents:
    project: Project
    dependent_projects: dict[str, Dependency]

    @property
    def name(self):
        return self.project.name
