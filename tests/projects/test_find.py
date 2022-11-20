import unittest

from pympl.projects.find import find_projects


class MyTestCase(unittest.TestCase):
    def test_find_all_projects(self):
        projects = find_projects()

        self.assertEqual(len(projects), 2)


if __name__ == '__main__':
    unittest.main()
