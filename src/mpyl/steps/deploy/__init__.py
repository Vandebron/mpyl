"""
Step implementations relating to the `Deploy` Stage
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...project import Project, load_project
from ...stages.discovery import find_invalidated_projects_for_stage
from ...utilities.repo import RepoConfig, Repository

STAGE_NAME = "deploy"


@dataclass(frozen=True)
class DeploySet:
    all_projects: set[Project]
    projects_to_deploy: set[Project]


def find_deploy_set(repo_config: RepoConfig, tag: Optional[str]) -> DeploySet:
    with Repository(repo_config) as repo:
        changes_in_branch = (
            repo.changes_in_tagged_commit(tag)
            if tag
            else repo.changes_in_branch_including_local()
        )
        project_paths = repo.find_projects()
        all_projects = set(
            map(lambda p: load_project(Path(""), Path(p), False), project_paths)
        )
        return DeploySet(
            all_projects,
            find_invalidated_projects_for_stage(
                all_projects, STAGE_NAME, changes_in_branch, None
            ),
        )
