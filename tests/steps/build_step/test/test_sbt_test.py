from src.mpyl.steps.models import Input
from src.mpyl.steps.test.sbt import TestSbt
from src.mpyl.utilities.sbt import SbtConfig
from tests.test_resources import test_data
from tests.test_resources.test_data import get_project


class TestBuildSbt:
    step_input = Input(get_project(), test_data.RUN_PROPERTIES, None)
    sbt_config = SbtConfig.from_config(config=step_input.run_properties.config)

    def test_sbt_test_compile_command_should_be_properly_constructed(self):
        command = TestSbt._construct_sbt_command(self.step_input, self.sbt_config,
                                                 TestSbt._construct_sbt_command_compile_with_coverage)
        assert ' '.join(command) == ('sbt -v -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled '
                                     '-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal project '
                                     'dockertest; coverageOn; test:compile')

    def test_sbt_test_test_command_should_be_properly_constructed(self):
        command = TestSbt._construct_sbt_command(self.step_input, self.sbt_config,
                                                 TestSbt._construct_sbt_command_test_with_coverage)
        assert ' '.join(command) == ('sbt -v -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled '
                                     '-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal project '
                                     'dockertest; test; coverageOff')

    def test_sbt_test_without_coverage_command_should_be_properly_constructed(self):
        sbt_config = self.sbt_config
        sbt_config_with_coverage = SbtConfig(sbt_config.java_opts, sbt_config.sbt_opts,
                                             sbt_command=sbt_config.sbt_command, test_with_coverage=False,
                                             verbose=False)
        command = TestSbt._construct_sbt_command(self.step_input, sbt_config_with_coverage,
                                                 TestSbt._construct_sbt_command_test_without_coverage)
        assert ' '.join(command) == ('sbt -J-Xmx4G -J-Xms4G -J-XX:+UseG1GC -J-XX:+CMSClassUnloadingEnabled '
                                     '-J-Xss2M -Duser.timezone=GMT -Djline.terminal=jline.UnixTerminal '
                                     'dockertest/test')
