import logging
import shutil

from unittest import mock
from pathlib import Path

from pyaml_env import parse_config

from src.mpyl.utilities.github import clone_repository
from src.mpyl.artifacts import BuildArtifacts
from src.mpyl.utilities.repo import RepoCredentials, Repository
from src.mpyl import RepoConfig
from tests import root_test_path


class TestArtifacts:
    test_branch = "pr-1234"
    resource_path = root_test_path / "cli" / "test_resources"
    config_path = root_test_path / "test_resources/mpyl_config.yml"
    run_properties_path = root_test_path / "test_resources/run_properties.yml"

    @mock.patch("src.mpyl.artifacts.BuildArtifacts.get_build_artifacts_paths")
    def test_push_pull_logic(self, mocked):
        tmp_folder = Path("tmp")
        test_build_artifacts = Path("test_resources/deployment/.mpyl")
        tmp_build_artifacts = tmp_folder / test_build_artifacts
        mocked.return_value = [tmp_build_artifacts]
        artifact_repo_config = RepoConfig(
            main_branch="main",
            ignore_patterns=[],
            repo_credentials=RepoCredentials(
                url="",
                ssh_url="git@github.com:Vandebron/mpyl-artifacts.git",
                user_name="",
                password="",
            ),
            folder=".artifacts",
        )
        repo_path = Path(root_test_path / artifact_repo_config.folder)
        print(repo_path)

        try:
            shutil.copytree(
                src=test_build_artifacts, dst=tmp_build_artifacts
            )  # copy test files to temporary folder
            clone_repository(artifact_repo_config)

            logger = logging.getLogger()
            config = parse_config(self.config_path)
            codebase_repo = Repository(config=RepoConfig.from_config(config))
            artifact_repo = Repository(config=artifact_repo_config)
            build_artifacts = BuildArtifacts(
                logger=logger,
                codebase_repo=codebase_repo,
                artifact_repo=artifact_repo,
            )
            build_artifacts.push(branch=self.test_branch)
            shutil.rmtree(tmp_folder, ignore_errors=True)
            build_artifacts.pull(branch=self.test_branch)
            assert tmp_build_artifacts.exists()
        finally:  # cleanup
            artifact_repo = Repository(
                config=artifact_repo_config
            )  # re-init since the previous init has to be in the try block, after cloning the repo
            artifact_repo.delete_remote_branch(branch_name=self.test_branch)
            shutil.rmtree(repo_path, ignore_errors=True)
            shutil.rmtree(tmp_folder, ignore_errors=True)
