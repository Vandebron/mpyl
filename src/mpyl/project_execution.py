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
        if cached:
            return ProjectExecution.skip(project, hashed_changes)
        return ProjectExecution.run(project, hashed_changes)

    @staticmethod
    def skip(project: Project, hashed_changes: Optional[str] = None):
        return ProjectExecution(
            project=project, hashed_changes=hashed_changes, cached=True
        )

    @staticmethod
    def run(project: Project, hashed_changes: Optional[str] = None):
        return ProjectExecution(
            project=project, hashed_changes=hashed_changes, cached=False
        )

    @property
    def name(self):
        return self.project.name
