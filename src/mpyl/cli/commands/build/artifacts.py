"""Build artifacts repo"""
import logging
from pathlib import Path

from ....artifacts.build_artifacts import ArtifactsRepository
from ....cli import CliContext
from ....utilities.repo import RepoConfig


def branch_name(target: str, artifact_type: str) -> str:
    return f"{target}-{artifact_type}"


def prepare_artifacts_repo(obj: CliContext, repo_path: Path) -> ArtifactsRepository:
    git_config = obj.config["vcs"].get("artifactRepository", None)
    if not git_config:
        raise ValueError("No artifact repository configured")
    artifact_repo_config: RepoConfig = RepoConfig.from_git_config(git_config=git_config)
    logger = logging.getLogger("mpyl")

    return ArtifactsRepository(
        logger=logger,
        codebase_repo=obj.repo,
        artifact_repo_config=artifact_repo_config,
        path_within_artifact_repo=repo_path,
    )
