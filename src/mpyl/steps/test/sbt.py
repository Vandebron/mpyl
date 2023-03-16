"""A step to compile and run tests for an SBT project"""
from logging import Logger
from typing import Callable

from .after_test import IntegrationTestAfter
from .before_test import IntegrationTestBefore
from .. import Input, Output, Step
from ..models import Artifact, input_to_artifact
from ...project import Stage, Project
from ...steps import Meta, ArtifactType
from ...utilities.junit import TEST_OUTPUT_PATH_KEY, to_test_suites, sum_suites
from ...utilities.sbt import SbtConfig
from ...utilities.subprocess import custom_check_output


class TestSbt(Step):
    def __init__(self, logger: Logger) -> None:
        meta = Meta(name='Sbt Test', description='Run sbt tests', version='0.0.1', stage=Stage.TEST)
        super().__init__(
            logger=logger,
            meta=meta,
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
            before=IntegrationTestBefore(logger),
            after=IntegrationTestAfter(logger)
        )

    def _test_with_coverage(self, step_input: Input, sbt_config: SbtConfig) -> Output:
        command_compile = self._construct_sbt_command(step_input, sbt_config,
                                                      self._construct_sbt_command_compile_with_coverage)
        compile_outcome = custom_check_output(self._logger, command_compile)
        project_name = step_input.project.name
        if not compile_outcome.success:
            return Output(success=False, message=f"Tests failed to compile for {project_name}",
                          produced_artifact=None)

        command_test = self._construct_sbt_command(step_input, sbt_config,
                                                   self._construct_sbt_command_test_with_coverage)
        test_outcome = custom_check_output(self._logger, command_test)
        if not test_outcome.success:
            return Output(success=False,
                          message=f"Tests failed to run for {project_name}. No test results have been recorded.",
                          produced_artifact=None)
        return Output(success=True, message="Success")

    def _test_without_coverage(self, step_input: Input, sbt_config: SbtConfig) -> Output:
        command_test_without_coverage = self._construct_sbt_command(step_input, sbt_config,
                                                                    self._construct_sbt_command_test_without_coverage)
        run_outcome = custom_check_output(self._logger, command_test_without_coverage)
        if not run_outcome.success:
            return Output(success=False, message=f"Tests without coverage failed to run for {step_input.project.name}",
                          produced_artifact=None)
        return Output(success=True, message="Success")

    def execute(self, step_input: Input) -> Output:
        project = step_input.project
        sbt_config = SbtConfig.from_config(config=step_input.run_properties.config)
        self._logger.debug(f'Config {sbt_config}')

        test_result = self._test_with_coverage(step_input, sbt_config) if sbt_config.test_with_coverage \
            else self._test_without_coverage(step_input, sbt_config)

        if not test_result.success:
            return test_result

        artifact = self._extract_test_report(project, step_input)
        suite = to_test_suites(artifact)
        summary = sum_suites(suite)
        return Output(success=summary.is_success,
                      message=f"Tests results produced for {project.name} ({summary})",
                      produced_artifact=artifact)

    @staticmethod
    def _construct_sbt_command_compile_with_coverage(step_input: Input) -> list[str]:
        return [
            f'project {step_input.project.name}',
            'coverageOn',
            'test:compile'
        ]

    @staticmethod
    def _construct_sbt_command_test_with_coverage(step_input: Input):
        return [
            f'project {step_input.project.name}',
            'test',
            'coverageOff'
        ]

    @staticmethod
    def _construct_sbt_command_test_without_coverage(step_input: Input):
        return [f'{step_input.project.name}/test']

    @staticmethod
    def _construct_sbt_command(step_input: Input, config: SbtConfig, commands_fn: Callable[[Input], list[str]]):
        command = config.to_command(config.test_with_client)
        command.append("; ".join(commands_fn(step_input)))
        return command

    @staticmethod
    def _extract_test_report(project: Project, step_input: Input) -> Artifact:
        return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                 spec={TEST_OUTPUT_PATH_KEY: f'{project.test_report_path}'})
