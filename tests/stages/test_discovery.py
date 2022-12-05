import unittest

from src.pympl.repo import Repository
from src.pympl.stage import Stage
from src.pympl.stages.discovery import find_invalidated_projects_for_stage


class TestDiscovery(unittest.TestCase):

    def test_should_find_invalidated_test_dependencies(self):
        repo = Repository('main')
        touched_files = {'tests/projects/service/file.py', 'tests/some_file.txt'}
        self.assertEqual(len(find_invalidated_projects_for_stage(repo, Stage.BUILD, touched_files)), 1)
        self.assertEqual(len(find_invalidated_projects_for_stage(repo, Stage.TEST, touched_files)), 2)

    def test_should_find_invalidated_dependencies(self):
        repo = Repository('main')
        invalidated = find_invalidated_projects_for_stage(repo, Stage.BUILD,
                                                          {'tests/projects/job/file.py', 'tests/some_file.txt'})
        self.assertEqual(1, len(invalidated))


if __name__ == '__main__':
    unittest.main()
