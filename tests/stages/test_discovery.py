import os

import pytest

from src.mpyl.project import Stage
from src.mpyl.repo import History
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from tests.test_resources import test_data


class TestDiscovery:

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ,
                        reason="fatal: detected dubious ownership in repository at '/github/workspace'")
    def test_should_find_invalidated_test_dependencies(self):
        repo = test_data.get_repo()
        touched_files = {'tests/projects/service/file.py', 'tests/some_file.txt'}
        assert len(find_invalidated_projects_for_stage(repo, Stage.BUILD, [History(0, "revision", touched_files)])) == 1
        assert len(find_invalidated_projects_for_stage(repo, Stage.TEST, [History(0, "revision", touched_files)])) == 0
        assert len(
            find_invalidated_projects_for_stage(repo, Stage.DEPLOY, [History(0, "revision", touched_files)])) == 1

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ,
                        reason="fatal: detected dubious ownership in repository at '/github/workspace'")
    def test_should_find_invalidated_dependencies(self):
        invalidated = find_invalidated_projects_for_stage(test_data.get_repo(), Stage.BUILD,
                                                          [History(0, "revision", {'tests/projects/job/file.py',
                                                                                   'tests/some_file.txt'})])
        assert 1 == len(invalidated)
