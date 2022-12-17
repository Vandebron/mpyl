import unittest

from src.pympl.projects.find import load_projects
from src.pympl.repo import Repository, RepoConfig


class ProjectLoadTestCase(unittest.TestCase):
    def test_load_all_projects(self):
        repo = Repository(RepoConfig({'cvs': {'git': {'main_branch': 'main'}}}))
        projects = load_projects(repo.root_dir(), repo.find_projects())

        self.assertEqual(len(projects), 2)


if __name__ == '__main__':
    unittest.main()
