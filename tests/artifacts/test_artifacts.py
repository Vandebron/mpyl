import logging
import os
from os.path import relpath
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.mpyl.artifacts.build_artifacts import (
    ArtifactsRepository,
    BuildCacheTransformer,
    ManifestPathTransformer,
    PathTransformer,
)
from src.mpyl.steps.deploy.k8s import DeployConfig
from src.mpyl.utilities.repo import RepoConfig
from src.mpyl.utilities.repo import RepoCredentials
from tests import test_resource_path, root_test_path
from tests.test_resources.test_data import get_repo, config_values


class TestTransformer(PathTransformer):
    root_folder: str

    def __init__(self, root_folder):
        self.root_folder = root_folder

    def artifact_type(self) -> str:
        return "test_type"

    def transform_for_read(self, project_path: str) -> Path:
        return Path(self.root_folder, project_path).parent

    def transform_for_write(self, artifact_path: str) -> Path:
        return Path(relpath(artifact_path, root_test_path))


class TestArtifacts:
    config_path = test_resource_path / "mpyl_config.yml"
    run_properties_path = test_resource_path / "run_properties.yml"

    artifact_repo_config = RepoConfig(
        main_branch="main",
        ignore_patterns=[],
        repo_credentials=RepoCredentials(
            url=f"https://{os.environ.get('GITHUB_CREDS')}@github.com/SamTheisens/mpyl-example-argocd.git",
            ssh_url="git@github.com:Vandebron/mpyl-artifacts.git",
            email="",
            user_name="",
            password="",
        ),
    )
    artifacts = ArtifactsRepository(
        logger=logging.getLogger(),
        codebase_repo=get_repo(),
        artifact_repo_config=artifact_repo_config,
        path_within_artifact_repo=Path("mpyl-cache"),
    )

    def test_build_cache_transformer(self):
        transformer = BuildCacheTransformer()
        assert transformer.transform_for_read("service/deployment/project.yml") == Path(
            "service/deployment/.mpyl"
        )

        assert transformer.transform_for_write("service/deployment/.mpyl") == Path(
            "service/deployment/.mpyl"
        )

    def test_manifest_transformer(self):
        deploy_config = DeployConfig.from_config(config_values)
        transformer = ManifestPathTransformer(deploy_config)
        assert transformer.transform_for_read("service/deployment/project.yml") == Path(
            "service/target/kubernetes"
        )

        assert transformer.transform_for_write("service/target/kubernetes") == Path(
            "service"
        )

    def test_copy_folders(self):
        with TemporaryDirectory() as tmp_repo_dir:
            project_paths = [
                str(
                    relpath(test_resource_path, root_test_path)
                    / Path("artifacts_test", "test_project.yml")
                )
            ]
            copied_files = self.artifacts.copy_files(
                project_paths, Path(tmp_repo_dir), TestTransformer(root_test_path)
            )
            assert copied_files == 1

    @pytest.mark.skip(reason="meant for local testing only")
    def test_clone_to_temp_dir(self):
        repository = get_repo()

        projects = repository.find_projects()
        self.artifacts.push(
            branch="test/build-artifacts",
            message="test message",
            project_paths=projects,
            path_transformer=BuildCacheTransformer(),
        )
