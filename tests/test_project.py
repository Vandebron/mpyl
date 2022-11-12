import unittest
from pathlib import Path
from os import path


from mpl.project import load_project
from mpl.target import Target


class TestMplSchema(unittest.TestCase):
    current_path = Path(path.dirname(path.realpath(__file__)))
    project_path = current_path / "test_resources" / "test_project.yml"

    def test_schema_load(self):
        project = load_project(str(self.project_path))
        self.assertEqual(project.name, 'nginx')
        self.assertEqual(project.maintainer, ['Marketplace', 'EV Home'])
        envs = project.deployment.properties.env

        first_env = [x for x in envs if x.key == 'ENV_NGINX_CONF_FOLDER'].pop()
        self.assertEqual(first_env.key, 'ENV_NGINX_CONF_FOLDER')
        self.assertEqual(first_env.get_value(Target.ACCEPTANCE), '/etc/nginx')


if __name__ == '__main__':
    unittest.main()
