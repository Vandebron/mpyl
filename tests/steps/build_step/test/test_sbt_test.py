import dataclasses

from src.mpyl.steps.models import Input
from src.mpyl.steps.test.sbt import TestSbt
from src.mpyl.utilities.sbt import SbtConfig
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project_execution


class TestBuildSbt:
    step_input = Input(get_project_execution(), test_data.RUN_PROPERTIES, None)
    sbt_config = SbtConfig.from_config(config=step_input.run_properties.config)

    def test_sbt_test_test_command_should_be_properly_constructed(self):
        command = TestSbt._construct_sbt_command(
            self.step_input.project_execution.name, self.sbt_config
        )
        assert " ".join(command) == (
            "sbt -v -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled "
            "-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal project "
            "dockertest; pullRemoteCache; coverageOn; test; coverageOff; pushRemoteCache"
        )

    def test_sbt_test_test_without_coverage_but_with_client_command_should_be_properly_constructed(
        self,
    ):
        sbt_config = self.sbt_config
        sbt_config_with_coverage = dataclasses.replace(
            sbt_config,
            test_with_coverage=False,
            test_with_client=True,
            verbose=False,
            remote_cache=False,
        )
        command = TestSbt._construct_sbt_command(
            self.step_input.project_execution.name, sbt_config_with_coverage
        )
        assert " ".join(command) == (
            "sbtn -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled "
            "-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal project "
            "dockertest; test"
        )
