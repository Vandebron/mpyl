from pathlib import Path

import pytest
from pyaml_env import parse_config

from src.pympl.project import load_project
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
        with(open(name_chart, 'w+')) as f:
            f.write(chart_yaml)
            assert not overwrite, "Should not commit with overwrite"

    with open(name_chart) as f:
        assert f.read() == chart_yaml


def _build_chart():
    project = load_project("", str(resource_path / "test_project.yml"), False)
    properties = BuildProperties("id", Target.PULL_REQUEST,
                                 VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None), {})
    return ServiceChart(step_input=Input(project, properties, None), image_name='registry/image:123').to_chart()


def test_load_config():
    yaml_values = parse_config(resource_path / "config.yml")
    config = DockerConfig(yaml_values)
    assert config.host_name == 'bigdataregistry.azurecr.io'


@pytest.mark.parametrize('template', ['deployment', 'service', 'serviceaccount', 'sealedsecrets'])
def test_chart_roundtrip(template):
    charts = _build_chart()
    _roundtrip(template_path, template, charts)
