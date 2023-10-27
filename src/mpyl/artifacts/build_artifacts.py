"""Class that handles remote caching of build artifacts"""
import abc
import os
import shutil
from abc import ABC
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory

from ..constants import BUILD_ARTIFACTS_FOLDER
from ..project import Project
from ..steps.deploy.k8s import DeployConfig
from ..utilities.repo import Repository, RepoConfig


class PathTransformer(ABC):
    @abc.abstractmethod
    def artifact_type(self) -> str:
        pass

    @abc.abstractmethod
    def transform_for_read(self, project_path: str) -> Path:
        pass

    @abc.abstractmethod
    def transform_for_write(self, artifact_path: str) -> Path:
        pass


class BuildCacheTransformer(PathTransformer):
    def artifact_type(self) -> str:
        return "build_artifacts"

    def transform_for_read(self, project_path: str) -> Path:
        return Path(
            project_path.replace(
                Project.project_yaml_path(), f"deployment/{BUILD_ARTIFACTS_FOLDER}"
            )
        )

    def transform_for_write(self, artifact_path: str) -> Path:
        return Path(artifact_path)


class ManifestPathTransformer(PathTransformer):
    deploy_config: DeployConfig

    def artifact_type(self) -> str:
        return "manifests"

    def __init__(self, deploy_config: DeployConfig):
        self.deploy_config = deploy_config

    def transform_for_read(self, project_path: str) -> Path:
        return Path(
            project_path.replace(
                Project.project_yaml_path(), self.deploy_config.output_path
            )
        )

    def transform_for_write(self, artifact_path: str) -> Path:
        return Path(artifact_path.replace(self.deploy_config.output_path, ""))


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
        if path_within_artifact_repo == Path("."):
            raise ValueError("Path within repo must not be root")
        self.path_within_artifact_repo = path_within_artifact_repo

    def pull(self, branch: str) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=Path(tmp_repo_dir)
            ) as artifact_repo:
                if not artifact_repo.remote_branch_exists(branch_name=branch):
                    self.logger.info(
                        f"Not pulling artifacts since branch {branch} does not exist in remote"
                    )
                    return

                self.logger.info(f"Fetching branch '{branch}' from remote")
                artifact_repo.checkout_branch(branch_name=branch)
                path_in_repo = repo_path / self.path_within_artifact_repo
                shutil.copytree(
                    src=path_in_repo,
                    dst=self.codebase_repo.root_dir.absolute(),
                    dirs_exist_ok=True,
                )

    def push(
        self,
        branch: str,
        message: str,
        project_paths: list[str],
        path_transformer: PathTransformer,
    ) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=repo_path
            ) as artifact_repo:
                branch_exists = artifact_repo.remote_branch_exists(branch_name=branch)
                if branch_exists:
                    self.logger.info(f"Fetching branch '{branch}' from remote")
                    artifact_repo.checkout_branch(branch_name=branch)
                else:
                    artifact_repo.create_branch(branch_name=branch)

                copied_paths = self.copy_files(
                    project_paths, repo_path, path_transformer
                )

                if not artifact_repo.has_changes:
                    self.logger.info("No changes detected, nothing to push")
                    return

                artifact_repo.stage(".")
                artifact_repo.commit(message)
                artifact_repo.push(branch)
                self.logger.info(
                    f"Pushed {branch} with {copied_paths} copied paths to {artifact_repo.remote_url}"
                )

    def copy_files(
        self,
        project_paths: list[str],
        repo_path: Path,
        transformer: PathTransformer,
    ) -> int:
        path_in_repo = repo_path / self.path_within_artifact_repo
        shutil.rmtree(path_in_repo, ignore_errors=True)

        artifact_paths = list(map(transformer.transform_for_read, project_paths))
        existing = [path for path in artifact_paths if path.exists() and path.is_dir()]
        for file_path in existing:
            repo_transformed = path_in_repo / transformer.transform_for_write(
                str(file_path)
            )
            self.logger.debug(f"Copying {file_path} to {repo_transformed}")
            os.makedirs(repo_transformed.parent, exist_ok=True)
            shutil.copytree(
                src=self.codebase_repo.root_dir.absolute() / file_path,
                dst=repo_transformed,
                dirs_exist_ok=True,
            )
        return len(existing)
