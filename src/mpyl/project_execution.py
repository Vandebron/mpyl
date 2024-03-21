"""This module contains the ProjectExecution class."""
import uuid
from dataclasses import dataclass

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    cache_key: str
    cached: bool

    @staticmethod
    def always_run(project: Project):
        """Create a ProjectExecution for a project that will always run, regardless of caching"""
        return ProjectExecution(
            project=project, cache_key=uuid.uuid4().hex, cached=False
        )

    @property
    def name(self):
        return self.project.name
