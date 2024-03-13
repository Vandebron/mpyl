"""This module contains the ProjectExecution class."""
from dataclasses import dataclass

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    cache_key: str
    cached: bool

    @staticmethod
    def always_run(project: Project):
        return ProjectExecution(
            project=project,
            cache_key="",  # Check if this should be a random string instead
            cached=False,
        )

    @property
    def name(self):
        return self.project.name
