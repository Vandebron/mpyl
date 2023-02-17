import os

import pytest

from src.mpyl.projects.find import load_projects
from tests.test_resources import test_data


class ProjectLoadTestCase:

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ,
                        reason="fatal: detected dubious ownership in repository at '/github/workspace'")
    def test_load_all_projects(self):
        repo = test_data.TEST_REPO
        projects = load_projects(repo.root_dir(), repo.find_projects())

        assert len(projects) == 2
