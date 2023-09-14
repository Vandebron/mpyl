import os
import logging
import shutil

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pyaml_env import parse_config

from src.mpyl.artifacts.build_artifacts import BuildArtifacts
from src.mpyl.utilities.repo import RepoCredentials, Repository
from src.mpyl import RepoConfig
from tests import root_test_path, test_resource_path


class TestArtifacts:
    test_branch = "unittest-tmp"
    config_path = test_resource_path / "mpyl_config.yml"
    run_properties_path = test_resource_path / "run_properties.yml"
    tmp_artifacts_dir = TemporaryDirectory(dir=".", prefix="tmp-")
    tmp_folder = Path(tmp_artifacts_dir.name)
    test_build_artifacts = Path("test_resources/deployment/.mpyl")
    tmp_build_artifacts = tmp_folder / test_build_artifacts

    @patch.object(
        target=BuildArtifacts,
        attribute="get_build_artifacts_paths",
        return_value=[tmp_build_artifacts],
    )
    def test_push_pull_logic(self, _mock1):
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
        )
        with TemporaryDirectory(dir=".", prefix="artifacts-") as tmp_repo_dir:
            repo_path = Path(tmp_repo_dir)
            artifact_repo = None

            try:
                shutil.copytree(
                    src=self.test_build_artifacts, dst=self.tmp_build_artifacts
                )  # copy test files to temporary folder
                logger = logging.getLogger()
                mpyl_config = parse_config(self.config_path)
                codebase_repo = Repository(config=RepoConfig.from_config(mpyl_config))
                artifact_repo = Repository.from_clone(
                    config=artifact_repo_config, repo_path=repo_path
                )
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
                if artifact_repo:
                    artifact_repo.delete_remote_branch(branch_name=self.test_branch)
                os.chdir(old_working_dir)
