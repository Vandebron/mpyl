import logging

from src.mpyl.steps.build.echo import BuildEcho
from src.mpyl.steps.models import Input
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project_execution


class TestBuildEcho:
    def test_build_echo(self):
        step_input = Input(get_project_execution(), test_data.RUN_PROPERTIES, None)
        echo = BuildEcho(logger=logging.getLogger())
        output = echo.execute(step_input)
        assert output.success
        assert output.message == "Built dockertest"
