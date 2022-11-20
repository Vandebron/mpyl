import unittest

from pympl.stages.discovery import find_invalidated_projects, find_changes_in_branch, find_changes_in_commit


class TestDiscovery(unittest.TestCase):
    def test_find_invalidated_projects(self):
        invalidated = find_invalidated_projects({'tests/projects/service/file.scala', 'tests/some_file.txt'})
        self.assertEqual(invalidated, {'tests/projects/service/'})

    def test_changes_in_commit_should_be_in_branch(self):
        changes_in_branch = find_changes_in_branch()
        changes_in_commit = find_changes_in_commit()

        self.assertTrue(changes_in_commit.issubset(changes_in_branch))


if __name__ == '__main__':
    unittest.main()
