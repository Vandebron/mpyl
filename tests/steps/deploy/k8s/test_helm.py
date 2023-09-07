import tempfile
from pathlib import Path

from src.mpyl.steps import Input
from src.mpyl.steps.deploy.k8s import DeployConfig, DeployAction
from src.mpyl.steps.deploy.k8s.chart import ChartBuilder, to_service_chart, DeploySet
from src.mpyl.steps.deploy.k8s.helm import write_chart, to_chart_metadata
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project


class TestHelm:
    def test_write_chart(self):
        output = test_data.get_output()
        project = get_project()
        step_input = Input(
            project,
            test_data.RUN_PROPERTIES,
            required_artifact=output.produced_artifact,
            dry_run=True,
        )
        with tempfile.TemporaryDirectory() as tempdir:
            builder = ChartBuilder(step_input, DeploySet({project}, {project}))
            write_chart(
                to_service_chart(builder),
                Path(tempdir),
                to_chart_metadata("chart_name", test_data.RUN_PROPERTIES),
            )

    def test_deploy_config_construction(self):
        config_values = test_data.get_config_values()
        assert config_values["kubernetes"]["deployAction"] == "KubectlManifest"

        deploy_config = DeployConfig.from_config(config_values)
        assert deploy_config.action.value is DeployAction.KUBERNETES_MANIFEST.value

    def test_use_helm_deploy_as_default(self):
        deploy_config = DeployConfig.from_config(
            {"kubernetes": {"outputPath": "output/path"}}
        )
        assert deploy_config.action.value is DeployAction.HELM_DEPLOY.value
