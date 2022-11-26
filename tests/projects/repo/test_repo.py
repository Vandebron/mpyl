import unittest

from pympl.repo import Repository


class RepoTestCase(unittest.TestCase):

    @unittest.skip("FIXME: main is not available in github action")
    def test_changes_in_commit_should_be_in_branch(self):
        repo = Repository('main')
        changes_in_branch = repo.changes_in_branch()
        changes_in_commit = repo.changes_in_commit()

        self.assertTrue(changes_in_commit.issubset(changes_in_branch))


if __name__ == '__main__':
    unittest.main()
