import unittest

from jsonschema import ValidationError

from src.pympl.project import load_project
from src.pympl.target import Target
from tests import root_test_path


class TestMplSchema(unittest.TestCase):
    resource_path = root_test_path / "test_resources"

    def test_schema_load(self):
        project = load_project("", str(self.resource_path / "test_project.yml"))
        self.assertEqual(project.name, 'dockertest')
        self.assertEqual(project.maintainer, ['Marketplace', 'Energy Trading'])
        envs = project.deployment.properties.env

        simple_env = [x for x in envs if x.key == 'SOME_ENV'].pop()
        self.assertEqual(simple_env.key, 'SOME_ENV')
        self.assertEqual(simple_env.get_value(Target.ACCEPTANCE), 'Acceptance')
        self.assertEqual(simple_env.get_value(Target.PRODUCTION), 'Production')

        self.assertEqual(project.dependencies.build, {'test/docker/'})
        self.assertEqual(project.dependencies.test, set())

        self.assertEqual(project.deployment.kubernetes.portMappings, {8080: 8080})
        self.assertEqual(project.deployment.kubernetes.livenessProbe.path.get_value(Target.ACCEPTANCE), '/health')
        self.assertEqual(project.deployment.kubernetes.metrics.enabled, False)

        host = project.deployment.traefik.hosts[0]
        self.assertEqual(host.host.get_value(Target.PULL_REQUEST_BASE), 'Host(`payments.test.vdbinfra.nl`)')
        self.assertEqual(host.tls.get_value(Target.PULL_REQUEST_BASE), 'le-custom-prod-wildcard-cert')

    def test_schema_load_validation(self):
        with self.assertRaises(ValidationError):
            load_project("", str(self.resource_path / "test_project_invalid.yml"))


if __name__ == '__main__':
    unittest.main()
