"""Class that handles remote caching of build artifacts"""
import abc
import os
import shutil
from abc import ABC
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory

from ..utilities.repo import Repository, RepoConfig


class PathTransformer(ABC):
    @abc.abstractmethod
    def transform(self, path: Path) -> Path:
        pass


class IdentityPathTransformer(PathTransformer):
    def transform(self, path: Path) -> Path:
        return path


class ManifestPathTransformer(PathTransformer):
    def transform(self, path: Path) -> Path:
        return Path(str(path).replace("target/kubernetes/", ""))


class ArtifactsRepository:
    logger: Logger
    codebase_repo: Repository
    artifact_repo_config: RepoConfig
    path_within_artifact_repo: Path

    def __init__(
        self,
        logger: Logger,
        codebase_repo: Repository,
        artifact_repo_config: RepoConfig,
        path_within_artifact_repo: Path,
    ):
        self.logger = logger
        self.codebase_repo = codebase_repo
        self.artifact_repo_config = artifact_repo_config
        if path_within_artifact_repo is Path("."):
            raise ValueError("Path within repo must not be root")
        self.path_within_artifact_repo = path_within_artifact_repo

    def pull(self, branch: str) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=Path(tmp_repo_dir)
            ) as artifact_repo:
                if artifact_repo.does_branch_exist(branch_name=branch):
                    self.logger.info(f"Fetching branch '{branch}' from remote")
                    artifact_repo.checkout_branch(branch_name=branch)
                self.logger.info(f"Branch {branch} does not exist in remote")

    def push(
        self,
        branch: str,
        file_paths: list[Path],
        path_transformer: PathTransformer = IdentityPathTransformer(),
    ) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=repo_path
            ) as artifact_repo:
                branch_exists = artifact_repo.does_branch_exist(branch_name=branch)
                if branch_exists:
                    self.logger.info(f"Fetching branch '{branch}' from remote")
                    artifact_repo.checkout_branch(branch_name=branch)
                else:
                    artifact_repo.create_branch(branch_name=branch)

                self.copy_files(file_paths, repo_path, path_transformer)

                if not artifact_repo.has_changes:
                    self.logger.info("No changes detected, nothing to push")
                    return

                artifact_repo.stage(".")
                artifact_repo.commit("test")
                artifact_repo.push(branch)
                self.logger.info(f"Pushed {branch} to {artifact_repo.remote_url}")

    def copy_files(
        self, file_paths: list[Path], repo_path: Path, path_transformer: PathTransformer
    ):
        path_in_repo = repo_path / self.path_within_artifact_repo
        shutil.rmtree(path_in_repo, ignore_errors=True)
        for file_path in file_paths:
            repo_transformed = path_in_repo / path_transformer.transform(file_path)
            self.logger.debug(f"Copying {file_path} to {repo_transformed}")
            os.makedirs(repo_transformed.parent, exist_ok=True)
            shutil.copytree(
                src=self.codebase_repo.root_dir.absolute() / file_path,
                dst=repo_transformed,
                dirs_exist_ok=True,
            )
