import unittest
from pathlib import Path
from os import path

from pympl.project import load_project
from pympl.target import Target


class TestMplSchema(unittest.TestCase):
    current_path = Path(path.dirname(path.realpath(__file__)))
    project_path = current_path / "test_resources" / "test_project.yml"

    def test_schema_load(self):
        project = load_project(str(self.project_path))
        self.assertEqual(project.name, 'nginx')
        self.assertEqual(project.maintainer, ['Marketplace', 'EV Home'])
        envs = project.deployment.properties.env

        simple_env = [x for x in envs if x.key == 'ENV_NGINX_CONF_FOLDER'].pop()
        self.assertEqual(simple_env.key, 'ENV_NGINX_CONF_FOLDER')
        self.assertEqual(simple_env.get_value(Target.ACCEPTANCE), '/etc/nginx')
        self.assertEqual(simple_env.get_value(Target.PRODUCTION), '/etc/nginx')

        multi_env = [x for x in envs if x.key == 'ENV_SERVER_NAME'].pop()
        self.assertEqual(multi_env.key, 'ENV_SERVER_NAME')
        self.assertEqual(multi_env.get_value(Target.PULL_REQUEST), 'test-{PR-NUMBER}.test.vdbinfra.nl')
        self.assertEqual(multi_env.get_value(Target.PULL_REQUEST_BASE), 'test.vdbinfra.nl')
        self.assertEqual(multi_env.get_value(Target.ACCEPTANCE), 'acceptance.vdbinfra.nl')
        self.assertEqual(multi_env.get_value(Target.PRODUCTION), 'vandebron.nl')


if __name__ == '__main__':
    unittest.main()
