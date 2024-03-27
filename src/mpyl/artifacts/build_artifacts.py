"""Class that handles remote caching of build artifacts"""
import abc
import os
import shutil
import time
from abc import ABC
from enum import Enum
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from git import GitCommandError
from github import Github

from ..cli.commands.build.jenkins import get_token
from ..constants import BUILD_ARTIFACTS_FOLDER
from ..project import Project, Target, load_project
from ..steps.deploy.k8s.deploy_config import DeployConfig, get_namespace
from ..steps.models import RunProperties
from ..utilities.github import GithubConfig
from ..utilities.repo import Repository, RepoConfig


class ArtifactType(str, Enum):
    CACHE = "cache"
    ARGO = "argo"


def get_argo_folder_name(target: Target) -> str:
    if target in (
        Target.PULL_REQUEST_BASE,
        Target.PULL_REQUEST,
    ):
        return "test"
    return target.name.lower()


class PathTransformer(ABC):
    @abc.abstractmethod
    def artifact_type(self) -> ArtifactType:
        pass

    @abc.abstractmethod
    def transform_for_read(self, project_path: str) -> Path:
        pass

    @abc.abstractmethod
    def transform_for_write(self, artifact_path: str, project: Project) -> Path:
        pass


class BuildCacheTransformer(PathTransformer):
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.CACHE

    def transform_for_read(self, project_path: str) -> Path:
        return Path(
            project_path.replace(
                Project.project_yaml_path(), f"deployment/{BUILD_ARTIFACTS_FOLDER}"
            )
        )

    def transform_for_write(self, artifact_path: str, project: Project) -> Path:
        return Path(artifact_path)


class ManifestPathTransformer(PathTransformer):
    deploy_config: DeployConfig
    run_properties: RunProperties

    def artifact_type(self) -> ArtifactType:
        return ArtifactType.ARGO

    def __init__(self, deploy_config: DeployConfig, run_properties: RunProperties):
        self.deploy_config = deploy_config
        self.run_properties = run_properties

    def transform_for_read(self, project_path: str) -> Path:
        return Path(
            project_path.replace(
                Project.project_yaml_path(), self.deploy_config.output_path
            )
        )

    def transform_for_write(self, artifact_path: str, project: Project) -> Path:
        argo_folder_name = get_argo_folder_name(target=self.run_properties.target)
        namespace = get_namespace(run_properties=self.run_properties, project=project)
        return Path(
            "k8s-manifests",
            project.name.lower(),
            argo_folder_name,
            namespace,
        )


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
        self.path_within_artifact_repo = path_within_artifact_repo

    def pull(self, branch: str) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=repo_path
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
        revision: str,
        repository_url: str,
        project_paths: list[str],
        path_transformer: PathTransformer,
        run_properties: RunProperties,
        github_config: Optional[GithubConfig] = None,
    ) -> None:
        with TemporaryDirectory() as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            with Repository.from_clone(
                config=self.artifact_repo_config, repo_path=repo_path
            ) as artifact_repo:
                remote_branch_exists = artifact_repo.remote_branch_exists(
                    branch_name=branch
                )
                if remote_branch_exists:
                    self.logger.info(f"Fetching branch '{branch}' from remote")
                    artifact_repo.checkout_branch(branch_name=branch)
                else:
                    artifact_repo.create_branch(branch_name=branch)
                    self.logger.info(f"Created branch '{branch}'")

                copied_paths = self.copy_files(
                    project_paths, repo_path, path_transformer
                )

                if artifact_repo.has_changes:
                    artifact_repo.stage(".")
                    artifact_repo.commit(f"Revision {revision} at {repository_url}")
                    artifact_repo.push(branch)

                    try:  # to prevent issues with parallel runs pushing to the same branch
                        self.logger.info("Pushing changes to remote")
                        artifact_repo.push(branch)
                    except GitCommandError:
                        self.logger.info("Retrying push after pulling from remote..")
                        time.sleep(1)
                        artifact_repo.pull()
                        artifact_repo.push(branch)

                    self.logger.info(
                        f"Pushed {branch} with {copied_paths} copied paths to {artifact_repo.remote_url}"
                    )
                else:
                    self.logger.info("No changes detected, nothing to push")
                    return

                if (
                    path_transformer.artifact_type() == ArtifactType.ARGO
                    and github_config
                ):
                    self.__create_pr(
                        github_config=github_config,
                        run_properties=run_properties,
                        revision=revision,
                        branch=branch,
                    )

    def copy_files(
        self,
        project_paths: list[str],
        repo_path: Path,
        transformer: PathTransformer,
    ) -> int:
        path_in_repo = repo_path / self.path_within_artifact_repo
        artifact_paths: dict[Path, Path] = {
            Path(project_path): transformer.transform_for_read(project_path)
            for project_path in project_paths
        }
        existing: dict[Path, Path] = {
            project_path: artifact_path
            for project_path, artifact_path in artifact_paths.items()
            if artifact_path.exists() and artifact_path.is_dir()
        }
        for project_path, file_path in existing.items():
            project = load_project(Path(""), project_path)
            repo_transformed = path_in_repo / transformer.transform_for_write(
                artifact_path=str(file_path), project=project
            )
            self.logger.debug(f"Copying {file_path} to {repo_transformed}")
            os.makedirs(repo_transformed.parent, exist_ok=True)
            shutil.copytree(
                src=self.codebase_repo.root_dir.absolute() / file_path,
                dst=repo_transformed,
                dirs_exist_ok=True,
            )
        return len(existing)

    def __create_pr(
        self,
        github_config: GithubConfig,
        run_properties: RunProperties,
        revision: str,
        branch: str,
    ):
        github = Github(login_or_token=get_token(github_config))
        repo = github.get_repo(github_config.repository)
        open_pulls = repo.get_pulls(head=branch)

        if open_pulls.totalCount == 0:
            body = f"""
## 🚀 Deploying
Docker tag: [{run_properties.versioning.identifier}]{f'({run_properties.details.change_url})' if run_properties.details.change_url else ''}
Commit: [{revision}]({self.codebase_repo.config.repo_credentials.url.removesuffix(".git")}/commit/{revision})

## 📍 To
Cluster: {get_argo_folder_name(target=run_properties.target)}

## 🧑‍💻️ Started by
[{run_properties.details.user}]
            """
            pr = repo.create_pull(
                title=branch,
                body=body,
                head=branch,
                base="main",
            )
            self.logger.info(
                f"Created pr in repo '{github_config.repository}' for branch '{branch}': {pr.html_url}"
            )
        else:
            self.logger.info(f"PR for branch '{branch}' is already open, doing nothing")
