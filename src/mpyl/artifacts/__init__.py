"""Class that handles remote caching of build artifacts"""

import shutil
from logging import Logger
from pathlib import Path

from ..project import load_project
from ..utilities.repo import Repository


CACHE_FOLDER_NAME = "cache"


class BuildArtifacts:
    logger: Logger
    codebase_repo: Repository
    artifact_repo: Repository
    cache_folder: Path

    def __init__(
        self,
        logger: Logger,
        codebase_repo: Repository,
        artifact_repo: Repository,
    ):
        self.logger = logger
        self.codebase_repo = codebase_repo
        self.artifact_repo = artifact_repo
        self.cache_folder = self.artifact_repo.root_dir / CACHE_FOLDER_NAME

    def get_build_artifacts_paths(self) -> list[Path]:
        found_projects: list[Path] = [
            Path(
                load_project(
                    self.codebase_repo.root_dir, Path(project_path), strict=False
                ).target_path
            )
            for project_path in self.codebase_repo.find_projects()
        ]

        return [path for path in found_projects if path.exists()]

    def pull(self, branch: str) -> None:
        if self.artifact_repo.does_branch_exist(branch_name=branch, remote=True):
            self.logger.info(f"Fetching branch '{branch}' from remote")
            self.artifact_repo.fetch_branch(branch_name=branch)
            self.artifact_repo.checkout_branch(branch_name=branch)

            for artifact_path in self.get_build_artifacts_paths():
                shutil.copytree(
                    src=self.cache_folder / artifact_path,
                    dst=artifact_path,
                    dirs_exist_ok=True,
                )
        else:
            self.logger.info(f"Branch '{branch}' has no remote to pull from")

    def push(self, branch: str) -> None:
        if self.artifact_repo.does_branch_exist(branch_name=branch):
            if self.artifact_repo.get_branch != branch:
                self.artifact_repo.checkout_branch(branch_name=branch)
        else:
            if self.artifact_repo.does_branch_exist(branch_name=branch, remote=True):
                self.logger.info(f"Fetching branch '{branch}' from remote")
                self.artifact_repo.fetch_branch(branch_name=branch)
                self.artifact_repo.checkout_branch(branch_name=branch)
            else:
                self.logger.info(f"Creating new branch '{branch}'")
                self.artifact_repo.create_branch(branch_name=branch)

        shutil.rmtree(self.cache_folder, ignore_errors=True)

        for artifact_path in self.get_build_artifacts_paths():
            shutil.copytree(src=artifact_path, dst=self.cache_folder / artifact_path)

        if self.artifact_repo.has_changes():
            self.logger.info("Committing and pushing all artifacts")
            self.artifact_repo.stage(CACHE_FOLDER_NAME)
            self.artifact_repo.commit(f"Add artifacts for {branch}")
            self.artifact_repo.push()
