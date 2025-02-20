"""This module contains the ProjectExecution class."""

from dataclasses import dataclass
from typing import Optional

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    changed_files: frozenset[str]
    hashed_changes: Optional[str]
    cached: bool

    @property
    def name(self):
        return self.project.name
