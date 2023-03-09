import os

import pytest

from src.mpyl.project import Stage
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.utilities.repo import History
from tests.test_resources import test_data


class TestDiscovery:

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ,
                        reason="fatal: detected dubious ownership in repository at '/github/workspace'")
    def test_should_find_invalidated_test_dependencies(self):
        repo = test_data.get_repo()
        touched_files = {'tests/projects/service/file.py', 'tests/some_file.txt'}
        projects = set(load_projects(repo.root_dir(), repo.find_projects()))
        assert len(
            find_invalidated_projects_for_stage(projects, Stage.BUILD, [History(0, "revision", touched_files)])) == 1
        assert len(
            find_invalidated_projects_for_stage(projects, Stage.TEST, [
                History(0, "revision", touched_files)])) == 2  # TODO: the tests say it's one, not sure what's changed
        assert len(
            find_invalidated_projects_for_stage(projects, Stage.DEPLOY, [History(0, "revision", touched_files)])) == 1

    @pytest.mark.skipif(condition="GITHUB_JOB" in os.environ,
                        reason="fatal: detected dubious ownership in repository at '/github/workspace'")
    def test_should_find_invalidated_dependencies(self):
        repo = test_data.get_repo()
        projects = set(load_projects(repo.root_dir(), repo.find_projects()))
        invalidated = find_invalidated_projects_for_stage(projects, Stage.BUILD,
                                                          [History(0, "revision", {'tests/projects/job/file.py',
                                                                                   'tests/some_file.txt'})])
        assert 1 == len(invalidated)
