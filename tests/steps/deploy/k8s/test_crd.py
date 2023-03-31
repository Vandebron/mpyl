from pathlib import Path

from mpyl.project import load_project
from mpyl.steps import Input
from mpyl.steps.deploy.k8s.chart import ChartBuilder
from test_resources import test_data
from tests import root_test_path


class TestCrdChart:
    def test_spark_chart(self):
        resource_path = root_test_path / 'projects' / 'spark-job' / 'deployment'
        step_input = Input(load_project(resource_path, Path('project.yml'), True), test_data.RUN_PROPERTIES, None)
        chart = ChartBuilder(step_input).create_chart()

        assert chart['spark'] is not None
        assert chart['spark'].spec['schedule'] == '0 7 * * *'
        assert chart['spark'].spec['template'] is not None
        assert chart['spark'].spec['template']['mainClass'] == \
               'nl.vandebron.batterypack.enrichchargesessions.EnrichChargeSessionsJobMain'
        assert chart['spark'].spec['template']['mainApplicationFile'] == \
               'local:///app/enrichchargesessionsjob-assembly-1.0.jar'
