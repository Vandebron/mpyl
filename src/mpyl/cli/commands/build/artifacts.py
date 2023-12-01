"""Build artifacts repo"""
import logging
from pathlib import Path

from ....artifacts.build_artifacts import (
    ArtifactsRepository,
    ArtifactType,
    get_argo_folder_name,
)
from ....cli import CliContext
from ....project import Target
from ....utilities.repo import RepoConfig


def branch_name(identifier: str, artifact_type: ArtifactType, target: Target) -> str:
    if artifact_type == ArtifactType.ARGO:
        return f"deploy/{get_argo_folder_name(target=target)}_{identifier}"
    return f"{identifier}-{artifact_type.value}"


def prepare_artifacts_repo(
    obj: CliContext, repo_path: Path, artifact_type: ArtifactType
) -> ArtifactsRepository:
    vcs = obj.config["vcs"]
    git_config = (
        vcs.get("cachingRepository")
        if artifact_type == ArtifactType.CACHE
        else vcs.get("argoRepository")
    )
    if git_config is None:
        raise ValueError(f"No repository for {artifact_type} configured")

    artifact_repo_config: RepoConfig = RepoConfig.from_git_config(git_config=git_config)
    logger = logging.getLogger("mpyl")

    return ArtifactsRepository(
        logger=logger,
        codebase_repo=obj.repo,
        artifact_repo_config=artifact_repo_config,
        path_within_artifact_repo=repo_path,
    )
