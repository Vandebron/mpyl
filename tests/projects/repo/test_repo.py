import os
import unittest

import pytest
from pyaml_env import parse_config

from src.mpyl.repo import RepoConfig
from src.mpyl.repo import Repository

from tests import root_test_path


class RepoTestCase:
    resource_path = root_test_path / "test_resources"

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ, reason="main is not available in github action")
    def test_changes_in_commit_should_be_in_branch(self):
        repo = Repository(RepoConfig({'cvs': {'git': 'mainBranch'}}))
        changes_in_branch = repo.changes_in_branch()
        changes_in_commit = repo.changes_in_commit()

        assert changes_in_commit.issubset(changes_in_branch), "should be subset"

    def test_load_config(self):
        yaml_values = parse_config(self.resource_path / "config.yml")
        config = RepoConfig(yaml_values)
        assert config.main_branch == 'main'


if __name__ == '__main__':
    unittest.main()
