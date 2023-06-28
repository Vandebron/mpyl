import os

import pytest

from src.mpyl.utilities.repo import RepoConfig
from tests import root_test_path
from tests.test_resources import test_data
from tests.test_resources.test_data import get_config_values


class TestRepo:
    resource_path = root_test_path / "test_resources"

    @pytest.mark.skipif(
        condition="GITHUB_JOB" in os.environ,
        reason="main is not available in github action",
    )
    def test_changes_local_and_un_versioned_should_be_included(self):
        with test_data.get_repo() as repo:
            changes_in_branch = repo.changes_in_branch_including_local()
            changes_in_commit = repo.changes_in_commit()

        assert changes_in_branch[-1].files_touched == changes_in_commit

    def test_load_config(self):
        config = RepoConfig.from_config(get_config_values())
        assert config.main_branch == "main"
        repo_credentials = config.repo_credentials
        assert repo_credentials.url == "https://github.com/acme/repo.git"
        assert (
            repo_credentials.to_url_with_credentials
            == "https://git-user:git-password@github.com/acme/repo.git"
        )
