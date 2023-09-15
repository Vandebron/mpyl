import logging

from src.mpyl.artifacts.build_artifacts import ArtifactsRepository
from src.mpyl.utilities.repo import RepoConfig
from src.mpyl.utilities.repo import RepoCredentials
from test_data import get_repo
from tests import test_resource_path


class TestArtifacts:
    test_branch = "unittest-tmp"
    config_path = test_resource_path / "mpyl_config.yml"
    run_properties_path = test_resource_path / "run_properties.yml"

    def test_clone_to_temp_dir(self):
        repository = get_repo()
        artifacts = ArtifactsRepository(
            logger=logging.getLogger(), codebase_repo=repository
        )
        artifact_repo_config = RepoConfig(
            main_branch="main",
            ignore_patterns=[],
            repo_credentials=RepoCredentials(
                url="https://<github_token>@github.com/SamTheisens/mpyl-example-argocd.git",
                ssh_url="git@github.com:Vandebron/mpyl-artifacts.git",
                user_name="",
                password="",
            ),
        )

        artifacts.pull(
            artifact_repo_config=artifact_repo_config, branch="test/build-artifacts"
        )
        artifacts.push(
            artifact_repo_config=artifact_repo_config, branch="test/build-artifacts"
        )
