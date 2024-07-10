from src.mpyl.steps.build.sbt import BuildSbt
from src.mpyl.steps.models import Input
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project_execution


class TestBuildSbt:
    def test_sbt_command_should_be_properly_constructed(self):
        step_input = Input(get_project_execution(), test_data.RUN_PROPERTIES, None)
        command = BuildSbt._construct_sbt_command(step_input, "imagename:latest")
        assert " ".join(command) == (
            "sbt -v -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled "
            "-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal project "
            'dockertest; set docker / imageNames := Seq(ImageName("imagename:latest")); '
            "docker"
        )
