import unittest

from pympl.repo import Repository
from pympl.stage import Stage
from pympl.stages.discovery import find_invalidated_projects_for_stage


class TestDiscovery(unittest.TestCase):

    def test_should_find_invalidated_test_dependencies(self):
        repo = Repository('main')
        invalidated = find_invalidated_projects_for_stage(repo, Stage.TEST,
                                                          {'tests/projects/service/file.py', 'tests/some_file.txt'})
        self.assertEqual(len(invalidated), 2)

    def test_should_find_invalidated_dependencies(self):
        repo = Repository('main')
        invalidated = find_invalidated_projects_for_stage(repo, Stage.BUILD,
                                                          {'tests/projects/job/file.py', 'tests/some_file.txt'})
        self.assertEqual(1, len(invalidated))


if __name__ == '__main__':
    unittest.main()
