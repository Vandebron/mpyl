"""This module contains the ProjectExecution class."""

from dataclasses import dataclass
from typing import Optional

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    hashed_changes: Optional[str]
    cached: bool

    @staticmethod
    def create(project: Project, cached: bool, hashed_changes: Optional[str] = None):
        return ProjectExecution(project, hashed_changes, cached)

    @property
    def name(self):
        return self.project.name
