import os
import logging
import shutil

from pathlib import Path
from unittest.mock import patch, PropertyMock
from pyaml_env import parse_config

from src.mpyl.artifacts.build_artifacts import BuildArtifacts
from src.mpyl.utilities.repo import RepoCredentials, Repository
from src.mpyl import RepoConfig
from tests import root_test_path, test_resource_path


class TestArtifacts:
    test_branch = "unittest-tmp"
    config_path = test_resource_path / "mpyl_config.yml"
    run_properties_path = test_resource_path / "run_properties.yml"
    tmp_folder = Path("tmp")
    test_build_artifacts = Path("test_resources/deployment/.mpyl")
    tmp_build_artifacts = tmp_folder / test_build_artifacts

    @patch(
        target="src.mpyl.artifacts.build_artifacts.BuildArtifacts.get_build_artifacts_paths",
        return_value=[tmp_build_artifacts],
    )
    @patch(
        target="src.mpyl.utilities.repo.Repository.root_dir",
        new_callable=PropertyMock,
        side_effect=[Path(root_test_path / ".artifacts"), root_test_path],
    )
    def test_push_pull_logic(self, _mock1, _mock2):
        old_working_dir = os.getcwd()
        os.chdir(
            root_test_path
        )  # to ensure actions in BuildArtifacts don't interfere with the real artifact repo
        shutil.rmtree(self.tmp_folder, ignore_errors=True)
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
        assert artifact_repo_config.folder == ".artifacts"
        repo_path = Path(root_test_path / artifact_repo_config.folder)

        try:
            shutil.copytree(
                src=self.test_build_artifacts, dst=self.tmp_build_artifacts
            )  # copy test files to temporary folder
            shutil.rmtree(repo_path, ignore_errors=True)

            logger = logging.getLogger()
            mpyl_config = parse_config(self.config_path)
            codebase_repo = Repository(config=RepoConfig.from_config(mpyl_config))
            artifact_repo = Repository.from_clone(config=artifact_repo_config)
            build_artifacts = BuildArtifacts(
                logger=logger,
                codebase_repo=codebase_repo,
                artifact_repo=artifact_repo,
            )
            build_artifacts.push(branch=self.test_branch)
            shutil.rmtree(self.tmp_folder, ignore_errors=True)
            build_artifacts.pull(branch=self.test_branch)
            assert self.tmp_build_artifacts.exists()
        finally:  # cleanup
            shutil.rmtree(self.tmp_folder, ignore_errors=True)
            artifact_repo = Repository(
                config=artifact_repo_config
            )  # re-init since the previous init has to be in the try block, after cloning the repo
            artifact_repo.delete_remote_branch(branch_name=self.test_branch)
            shutil.rmtree(repo_path, ignore_errors=True)
            os.chdir(old_working_dir)
