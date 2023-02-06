import unittest

import pytest

from src.mpyl.repo import Repository, RepoConfig, History
from src.mpyl.stage import Stage
from src.mpyl.stages.discovery import find_invalidated_projects_for_stage


class TestDiscovery(unittest.TestCase):

    @pytest.skip(reason='Does not work in github action due to repo ownership issue', allow_module_level=True)
    def test_should_find_invalidated_test_dependencies(self):
        repo = Repository(RepoConfig({'cvs': {'git': {'main_branch': 'main'}}}))
        touched_files = {'tests/projects/service/file.py', 'tests/some_file.txt'}
        assert len(find_invalidated_projects_for_stage(repo, Stage.BUILD, [History(0, "revision", touched_files)])) == 1
        assert len(find_invalidated_projects_for_stage(repo, Stage.TEST, [History(0, "revision", touched_files)])) == 0
        assert len(
            find_invalidated_projects_for_stage(repo, Stage.DEPLOY, [History(0, "revision", touched_files)])) == 1

    def test_should_find_invalidated_dependencies(self):
        repo = Repository(RepoConfig({'cvs': {'git': {'main_branch': 'main'}}}))
        invalidated = find_invalidated_projects_for_stage(repo, Stage.BUILD,
                                                          [History(0, "revision", {'tests/projects/job/file.py',
                                                                                   'tests/some_file.txt'})])
        assert 1 == len(invalidated)


if __name__ == '__main__':
    unittest.main()
