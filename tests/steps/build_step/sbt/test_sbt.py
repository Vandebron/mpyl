from src.mpyl.steps.build.sbt import BuildSbt
from src.mpyl.steps.models import Input
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project


class TestBuildSbt:

    def test_sbt_command_should_be_properly_constructed(self):
        step_input = Input(get_project(), test_data.RUN_PROPERTIES, None)
        command = BuildSbt._construct_sbt_command(step_input, 'imagename:latest')
        assert command == ['sbt',
                           'project dockertest; set docker / imageNames := Seq(ImageName("imagename:latest")); '
                           'scalafmtCheckAll; docker']
