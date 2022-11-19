import unittest

from pympl.projects.find import find_projects


class MyTestCase(unittest.TestCase):
    def test_something(self):
        projects = find_projects()

        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].name, 'job')
        self.assertEqual(projects[1].name, 'service')


if __name__ == '__main__':
    unittest.main()
