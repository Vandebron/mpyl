"""Class that handles remote caching of build artifacts"""
import shutil
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory

from ..utilities.repo import Repository, RepoConfig


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
        path_within_artifact_repo: Path = Path("."),
    ):
        self.logger = logger
        self.codebase_repo = codebase_repo
        self.artifact_repo_config = artifact_repo_config
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

    def push(self, branch: str, file_paths: list[Path]) -> None:
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

                shutil.rmtree(repo_path, ignore_errors=True)
                for file_path in file_paths:
                    shutil.copytree(
                        src=file_path,
                        dst=repo_path / self.path_within_artifact_repo / file_path.name,
                        dirs_exist_ok=True,
                    )

                git = artifact_repo._repo.git
                git.add(".")
                git.commit("-m", "test")
                git.push(
                    "--set-upstream", "origin", branch
                ) if not branch_exists else git.push()
                self.logger.info(f"Pushed {branch} to {artifact_repo.remote_url}")
