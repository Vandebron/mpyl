import logging

from src.mpyl.steps.scan.echo import ScanEcho
from src.mpyl.steps.models import Input
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project


class TestBuildEcho:

    def test_scan_echo(self):
        step_input = Input(get_project(), test_data.RUN_PROPERTIES, None)
        echo = ScanEcho(logger=logging.getLogger())
        output = echo.execute(step_input)
        assert output.success
        assert output.message == 'Scanned dockertest'