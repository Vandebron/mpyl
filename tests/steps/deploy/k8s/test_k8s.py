import unittest
from pathlib import Path

from ruamel.yaml import YAML

from src.pympl.project import load_project
from src.pympl.steps.build import DockerConfig
from src.pympl.steps.deploy.k8s.service import ServiceChart
from src.pympl.steps.models import Input, BuildProperties, VersioningProperties
from src.pympl.target import Target
from tests import root_test_path


class K8sTestCase(unittest.TestCase):
    resource_path = root_test_path / "test_resources"
    template_path = root_test_path / "steps" / "deploy" / "k8s" / "chart" / "templates"

    def _roundtrip(self, file_name: Path, chart: str, as_yaml: dict[str, str], overwrite: bool = False):
        name_chart = file_name / f"{chart}.yaml"
        chart_yaml = as_yaml[chart]
        if overwrite:
            with(open(name_chart, 'w+')) as f:
                f.write(chart_yaml)
                self.assertEqual(overwrite, False, "Should not commit with overwrite")

        with open(name_chart) as f:
            self.assertEqual(f.read(), chart_yaml)

    def _build_chart(self):
        project = load_project("", str(self.resource_path / "test_project.yml"), False)
        properties = BuildProperties("id", Target.PULL_REQUEST,
                                     VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None), {})
        return ServiceChart(step_input=Input(project, properties, None)).to_chart()

    def test_load_config(self):
        yaml_path = self.resource_path / "config.yml"
        with open(yaml_path) as f:
            yaml = YAML()
            yaml_values = yaml.load(f)
            config = DockerConfig(yaml_values)
            self.assertEqual(config.host_name, 'bigdataregistry.azurecr.io')

    def test_deployment(self):
        sd = self._build_chart()
        self._roundtrip(self.template_path, 'deployment', sd)

    def test_service(self):
        sd = self._build_chart()
        self._roundtrip(self.template_path, 'service', sd)

    def test_service_account(self):
        sd = self._build_chart()
        self._roundtrip(self.template_path, 'serviceaccount', sd)

    def test_sealed_secrets(self):
        sd = self._build_chart()
        self._roundtrip(self.template_path, 'sealedsecrets', sd)


if __name__ == '__main__':
    unittest.main()
