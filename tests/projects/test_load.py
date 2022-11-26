import unittest

from pympl.projects.find import load_projects
from pympl.repo import Repository


class ProjectLoadTestCase(unittest.TestCase):
    def test_load_all_projects(self):
        repo = Repository('main')
        projects = load_projects(repo.root_dir(), repo.find_projects())

        self.assertEqual(len(projects), 2)


if __name__ == '__main__':
    unittest.main()
