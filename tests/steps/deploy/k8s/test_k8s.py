from pathlib import Path

import pytest
from kubernetes.client import V1Probe, V1ObjectMeta
from pyaml_env import parse_config

from src.mpyl.project import Target, Project
from src.mpyl.steps.deploy.k8s.chart import ChartBuilder, to_service_chart, to_job_chart, to_cron_job_chart
from src.mpyl.steps.deploy.k8s.resources.crd import to_yaml, CustomResourceDefinition
from src.mpyl.steps.deploy.k8s.resources.customresources import V1AlphaIngressRoute
from src.mpyl.steps.models import Input, Artifact, ArtifactType
from src.mpyl.utilities.docker import DockerConfig
from tests import root_test_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip, get_project, get_job_project


class TestKubernetesChart:
    resource_path = root_test_path / "test_resources"
    template_path = root_test_path / "steps" / "deploy" / "k8s" / "chart" / "templates"

    config = parse_config(resource_path / "mpyl_config.yml")
    liveness_probe_defaults = config['project']['deployment']['kubernetes']['livenessProbe']

    @staticmethod
    def _roundtrip(file_name: Path, chart: str, resources: dict[str, CustomResourceDefinition],
                   overwrite: bool = False):
        name_chart = file_name / f"{chart}.yaml"
        resource = resources[chart]
        assert_roundtrip(name_chart, to_yaml(resource), overwrite)

    @staticmethod
    def _get_builder(project: Project):
        required_artifact = Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE, revision="revision",
            producing_step="build_docker_Step",
            spec={'image': 'registry/image:123'}
        )
        return ChartBuilder(
            step_input=Input(project, run_properties=test_data.RUN_PROPERTIES,
                             required_artifact=required_artifact)
        )

    def test_probe_values_should_be_customizable(self):
        project = test_data.get_project()
        probe = project.kubernetes.liveness_probe

        custom_success_threshold = 0
        custom_failure_threshold = 99

        assert probe.values['successThreshold'] == custom_success_threshold
        assert probe.values['failureThreshold'] == custom_failure_threshold

        v1_probe: V1Probe = ChartBuilder._to_probe(probe, self.liveness_probe_defaults, target=Target.PULL_REQUEST)
        assert v1_probe.success_threshold == custom_success_threshold
        assert v1_probe.failure_threshold == custom_failure_threshold

        assert v1_probe.period_seconds == self.liveness_probe_defaults['periodSeconds']
        assert v1_probe.grpc.port == 123

    def test_probe_deserialization_failure_should_throw(self):
        project = test_data.get_project()
        probe = project.kubernetes.liveness_probe

        probe.values['httpGet'] = 'incorrect'

        with pytest.raises(ValueError) as exc_info:
            ChartBuilder._to_probe(probe, self.liveness_probe_defaults, target=Target.PULL_REQUEST)
        assert 'Invalid value for `port`, must not be `None`' in str(exc_info.value)

    def test_load_config(self):
        yaml_values = parse_config(self.resource_path / "mpyl_config.yml")
        docker_config = DockerConfig.from_dict(yaml_values)
        assert docker_config.host_name == 'bigdataregistry.azurecr.io'

    def test_should_validate_against_crd_schema(self):
        project = test_data.get_project()
        route = V1AlphaIngressRoute(metadata=V1ObjectMeta(), hosts=project.deployment.traefik.hosts, service_port=1234,
                                    name='serviceName', target=Target.PRODUCTION)
        route.spec['tls'] = {'secretName': 1234}

        with pytest.raises(ValueError) as exc_info:
            to_yaml(route)
        assert "Schema validation failed with 1234 is not of type 'string'" in str(exc_info.value)

    @pytest.mark.parametrize('template',
                             ['deployment', 'service', 'serviceaccount', 'sealedsecrets', 'ingress-https-route'])
    def test_service_chart_roundtrip(self, template):
        builder = self._get_builder(get_project())
        chart = to_service_chart(builder)
        self._roundtrip(self.template_path / "service", template, chart)

    @pytest.mark.parametrize('template', ['job', 'serviceaccount', 'sealedsecrets'])
    def test_job_chart_roundtrip(self, template):
        builder = self._get_builder(get_job_project())
        chart = to_job_chart(builder)
        self._roundtrip(self.template_path / "job", template, chart)

    def test_cron_job_chart_roundtrip(self):
        builder = self._get_builder(get_job_project())
        chart = to_cron_job_chart(builder)
        self._roundtrip(self.template_path / "cronjob", 'cronjob', chart)
