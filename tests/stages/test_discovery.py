import unittest

from pympl.stages.discovery import find_invalidated_projects


class TestDiscovery(unittest.TestCase):
    def test_find_invalidated_projects(self):
        invalidated = find_invalidated_projects({'tests/projects/service/file.scala', 'tests/some_file.txt'})
        self.assertEqual(invalidated, {'tests/projects/service/'})


if __name__ == '__main__':
    unittest.main()
