import unittest

from src.pympl.project import load_project
from src.pympl.steps.deploy.k8s.service import ServiceDeployment, to_yaml
from src.pympl.steps.models import Input, BuildProperties, VersioningProperties
from src.pympl.target import Target
from tests import root_test_path


class K8sTestCase(unittest.TestCase):
    resource_path = root_test_path / "test_resources"
    template_path = root_test_path / "steps" / "deploy" / "k8s" / "chart" / "templates"

    def roundtrip(self, bla: str, resource: object, overwrite: bool = False):
        as_yaml = to_yaml(resource)
        if overwrite:
            with(open(bla, 'w+')) as f:
                f.write(as_yaml)
                self.assertEqual(overwrite, False)

        with open(bla) as f:
            self.assertEqual(f.read(), as_yaml, "Should not commit with overwrite")

    def test_deployment(self):
        project = load_project("", str(self.resource_path / "test_project.yml"), False)

        properties = BuildProperties("id", Target.PULL_REQUEST,
                                     VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None))
        sd = ServiceDeployment(step_input=Input(project, properties, None))
        deployment = sd.to_deployment()

        self.roundtrip(self.template_path / 'service.yaml', deployment)


if __name__ == '__main__':
    unittest.main()
