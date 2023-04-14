import os

import pytest

from src.mpyl.project import Stage
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage
from src.mpyl.utilities.repo import Revision
from tests import root_test_path
from tests.test_resources import test_data


class TestDiscovery:

    def test_should_find_invalidated_test_dependencies(self):
        with test_data.get_repo() as repo:
            touched_files = {'tests/projects/caching-service/service/file.py', 'tests/some_file.txt'}
            projects = set(load_projects(repo.root_dir(), repo.find_projects()))
            assert len(find_invalidated_projects_for_stage(projects, Stage.BUILD,
                                                           [Revision(0, "revision", touched_files)])) == 1
            assert len(find_invalidated_projects_for_stage(projects, Stage.TEST,
                                                           [Revision(0, "revision", touched_files)])) == 2
            assert len(find_invalidated_projects_for_stage(projects, Stage.DEPLOY,
                                                           [Revision(0, "revision", touched_files)])) == 1

    def test_should_find_invalidated_dependencies(self):
        projs = {'projects/job/deployment/project.yml', 'projects/caching-service/service/deployment/project.yml',
                 'projects/sbt-service/deployment/project.yml'}
        projects = set(load_projects(root_test_path, projs))
        invalidated = find_invalidated_projects_for_stage(projects, Stage.BUILD,
                                                          [Revision(0, "hash", {'projects/job/file.py',
                                                                                'some_file.txt'})])
        assert 1 == len(invalidated)
