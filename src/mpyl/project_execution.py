"""This module contains the ProjectExecution class."""
from dataclasses import dataclass

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    changed_files: frozenset[str]
    cache_key: str
    cached: bool

    @staticmethod
    def files_changed(project: Project, files: set[str], cache_key: str, cached: bool):
        return ProjectExecution(
            project=project,
            changed_files=frozenset(files),
            cache_key=cache_key,
            cached=cached
        )

    @staticmethod
    def dependency_touched(project: Project, cache_key: str, cached: bool):
        return ProjectExecution(
            project=project,
            changed_files=frozenset(),
            cache_key=cache_key,
            cached=cached
        )

    @staticmethod
    def always_run(project: Project):
        return ProjectExecution(
            project=project,
            changed_files=frozenset(),
            cache_key="",  # TODO check if this should be a random string instead
            cached=False
        )

    @property
    def name(self):
        return self.project.name
