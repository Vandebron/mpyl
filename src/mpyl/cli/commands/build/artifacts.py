"""Build artifacts repo"""
import logging
from pathlib import Path

from ....artifacts.build_artifacts import ArtifactsRepository
from ....cli import CliContext
from ....utilities.repo import RepoConfig


def branch_name(target: str, artifact_type: str) -> str:
    return f"{target}-{artifact_type}"


def prepare_artifacts_repo(
    obj: CliContext, repo_path: Path, artifact_type: str
) -> ArtifactsRepository:
    vcs = obj.config["vcs"]
    git_config = (
        vcs.get("cachingRepository")
        if artifact_type == "cache"
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
