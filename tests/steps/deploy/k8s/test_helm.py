import tempfile

from src.mpyl.steps import Input
from src.mpyl.steps.deploy.k8s.chart import ChartBuilder, to_service_chart
from src.mpyl.steps.deploy.k8s.helm import write_chart, to_chart_metadata
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project


class TestHelm:
    def test_write_chart(self):
        output = test_data.get_output()
        step_input = Input(get_project(), test_data.RUN_PROPERTIES, required_artifact=output.produced_artifact,
                           dry_run=True)
        with tempfile.TemporaryDirectory() as tempdir:
            builder = ChartBuilder(step_input)
            write_chart(to_service_chart(builder), tempdir, to_chart_metadata('chart_name', test_data.RUN_PROPERTIES))
