import unittest
from pathlib import Path
from os import path

from pympl.project import load_project
from pympl.target import Target


class TestMplSchema(unittest.TestCase):
    current_path = Path(path.dirname(path.realpath(__file__)))
    resource_path = current_path / "test_resources"

    def test_schema_load(self):
        project = load_project(str(self.resource_path / "test_project.yml"))
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

        self.assertEqual(project.dependencies.build, ['apps/', 'server/', 'nginx-gateway/', 'client'])
        self.assertEqual(project.dependencies.test, None)

        self.assertEqual(project.deployment.kubernetes.portMappings, {9090: 80, 9091: 84})
        self.assertEqual(project.deployment.kubernetes.livenessProbe.path.get_value(Target.ACCEPTANCE), '/health')
        self.assertEqual(project.deployment.kubernetes.metrics.enabled, False)

        host = project.deployment.traefik.hosts[0]
        self.assertEqual(host.host.get_value(Target.PULL_REQUEST_BASE),
                         'HostRegexp(`{subdomain:(bewindvoering|ev|mijn|nom|vrienden|werkenbij|www|blog){1}}'
                         '.test.vdbinfra.nl`, `test.vdbinfra.nl`)')
        self.assertEqual(host.tls.get_value(Target.PULL_REQUEST_BASE), 'le-production-frontend-wildcard-cert')
        self.assertEqual(host.whitelists.get_value(Target.ACCEPTANCE),
                         ['NAT-Gateway-Service', 'Salesforce', 'K8s-Acceptance'])

    def test_schema_load_validation(self):
        project = load_project(str(self.resource_path / "test_project_invalid.yml"))
        self.assertEqual(project, None)


if __name__ == '__main__':
    unittest.main()
