from pathlib import Path

import pytest

from mpyl.project import load_project
from mpyl.steps import Input
from mpyl.steps.deploy.k8s.chart import ChartBuilder
from mpyl.steps.deploy.k8s.resources.crd import to_yaml
from tests import root_test_path
from tests.test_resources import test_data


def get_builder_for_resource(resource_path: Path) -> ChartBuilder:
    step_input = Input(load_project(resource_path, Path('project.yml'), True), test_data.RUN_PROPERTIES, None)
    return ChartBuilder(step_input)


class TestCrdChart:
    def test_construct_crd_spark_chart(self):
        resource_path = root_test_path / 'projects' / 'spark-job' / 'deployment'
        chart = get_builder_for_resource(resource_path).create_chart()

        assert chart['spark'] is not None
        assert chart['spark'].spec['schedule'] == '0 7 * * *'
        assert chart['spark'].spec['template'] is not None
        assert chart['spark'].spec['template']['mainClass'] == \
               'nl.vandebron.batterypack.enrichchargesessions.EnrichChargeSessionsJobMain'
        assert chart['spark'].spec['template']['mainApplicationFile'] == \
               'local:///app/enrichchargesessionsjob-assembly-1.0.jar'

    def test_validate_crd_spark_chart(self):
        resource_path = root_test_path / 'projects' / 'spark-job' / 'deployment'
        chart = get_builder_for_resource(resource_path).create_chart()

        chart['spark'].spec = {'arguments': [1]}  # arguments should be a list of string

        with pytest.raises(ValueError):
            to_yaml(chart['spark'])
