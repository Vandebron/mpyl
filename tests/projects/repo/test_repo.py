import os

import pytest
from pyaml_env import parse_config

from src.mpyl.utilities.repo import RepoConfig
from tests import root_test_path
from tests.test_resources import test_data


class TestRepo:
    resource_path = root_test_path / "test_resources"

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ, reason="main is not available in github action")
    def test_changes_local_and_un_versioned_should_be_included(self):
        repo = test_data.get_repo()
        changes_in_branch = repo.changes_in_branch_including_local()
        changes_in_commit = repo.changes_in_commit()

        assert changes_in_branch[-1].files_touched == changes_in_commit

    def test_load_config(self):
        yaml_values = parse_config(self.resource_path / "config.yml")
        config = RepoConfig(yaml_values)
        assert config.main_branch == 'main'
