from pathlib import Path

import pytest
from kubernetes.client import V1Probe
from pyaml_env import parse_config

from src.pympl.project import load_project, Probe
from src.pympl.steps.build import DockerConfig
from src.pympl.steps.deploy.k8s.service import ServiceChart
from src.pympl.steps.models import Input, BuildProperties, VersioningProperties
from src.pympl.target import Target
from tests import root_test_path

resource_path = root_test_path / "test_resources"
template_path = root_test_path / "steps" / "deploy" / "k8s" / "chart" / "templates"


def _roundtrip(file_name: Path, chart: str, as_yaml: dict[str, str], overwrite: bool = False):
    name_chart = file_name / f"{chart}.yaml"
    chart_yaml = as_yaml[chart]
    if overwrite:
        with open(name_chart, 'w+', encoding='utf-8') as file:
            file.write(chart_yaml)
            assert not overwrite, "Should not commit with overwrite"

    with open(name_chart, encoding='utf-8') as file:
        assert file.read() == chart_yaml


def _build_chart():
    project = load_project("", str(resource_path / "test_project.yml"), False)
    properties = BuildProperties("id", Target.PULL_REQUEST,
                                 VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None), {})
    return ServiceChart(step_input=Input(project, properties, None), image_name='registry/image:123').to_chart()


def test_probe_values_should_be_customizable():
    project = load_project("", str(resource_path / "test_project.yml"), False)
    probe = project.kubernetes.liveness_probe

    custom_success_threshold = 0
    custom_failure_threshold = 99

    assert probe.values['successThreshold'] == custom_success_threshold
    assert probe.values['failureThreshold'] == custom_failure_threshold

    v1_probe: V1Probe = ServiceChart._to_probe(probe, Probe.LIVENESS_PROBE_DEFAULTS, target=Target.PULL_REQUEST)
    assert v1_probe.success_threshold == custom_success_threshold
    assert v1_probe.failure_threshold == custom_failure_threshold

    assert v1_probe.period_seconds == Probe.LIVENESS_PROBE_DEFAULTS['periodSeconds']
    assert v1_probe.grpc.port == 123


def test_probe_deserialization_failure_should_throw():
    project = load_project("", str(resource_path / "test_project.yml"), False)
    probe = project.kubernetes.liveness_probe

    probe.values['httpGet'] = 'incorrect'

    with pytest.raises(ValueError) as excinfo:
        ServiceChart._to_probe(probe, Probe.LIVENESS_PROBE_DEFAULTS, target=Target.PULL_REQUEST)
    assert 'Invalid value for `port`, must not be `None`' in str(excinfo.value)


def test_load_config():
    yaml_values = parse_config(resource_path / "config.yml")
    config = DockerConfig(yaml_values)
    assert config.host_name == 'bigdataregistry.azurecr.io'


@pytest.mark.parametrize('template', ['deployment', 'service', 'serviceaccount', 'sealedsecrets'])
def test_chart_roundtrip(template):
    charts = _build_chart()
    _roundtrip(template_path, template, charts)
