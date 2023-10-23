""" Discovery of projects that are relevant to a specific `mpyl.stage.Stage` . Determine which of the
discovered projects have been invalidated due to changes in the source code since the last build of the project's
output artifact."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..project import Project, load_project
from ..project import Stage
from ..steps import deploy
from ..steps.models import Output
from ..utilities.repo import Revision, RepoConfig, Repository


@dataclass(frozen=True)
class DeploySet:
    all_projects: set[Project]
    projects_to_deploy: set[Project]


def is_invalidated(project: Project, stage: str, path: str) -> bool:
    deps = project.dependencies
    deps_for_stage = deps.set_for_stage(stage) if deps else {}

    touched_dependency = (
        next(filter(path.startswith, deps_for_stage), None) if deps else None
    )
    startswith: bool = path.startswith(project.root_path)
    return startswith or touched_dependency is not None


def output_invalidated(output: Optional[Output], revision_hash: str) -> bool:
    if output is None:
        return True
    if not output.success:
        return True
    if output.produced_artifact is None:
        return True
    artifact = output.produced_artifact
    if artifact.revision != revision_hash:
        return True

    return False


def _to_relevant_changes(
    project: Project, stage: str, change_history: list[Revision]
) -> set[str]:
    output: Output = Output.try_read(project.target_path, stage)
    relevant = set()
    for history in reversed(sorted(change_history, key=lambda c: c.ord)):
        if stage == deploy.STAGE_NAME or output_invalidated(output, history.hash):
            relevant.update(history.files_touched)
        else:
            return relevant

    return relevant


def _are_invalidated(
    project: Project, stage: str, change_history: list[Revision]
) -> bool:
    if project.stages.for_stage(stage) is None:
        return False

    relevant_changes = _to_relevant_changes(project, stage, change_history)
    return (
        len(set(filter(lambda c: is_invalidated(project, stage, c), relevant_changes)))
        > 0
    )


def find_invalidated_projects_for_stage(
    all_projects: set[Project], stage: str, change_history: list[Revision]
) -> set[Project]:
    return set(
        filter(lambda p: _are_invalidated(p, stage, change_history), all_projects)
    )


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
                all_projects, deploy.STAGE_NAME, changes_in_branch
            ),
        )


def for_stage(projects: set[Project], stage: Stage) -> set[Project]:
    return set(filter(lambda p: p.stages.for_stage(stage.name), projects))
