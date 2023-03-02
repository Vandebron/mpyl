"""A step to compile and run tests for an Sbt project"""
from logging import Logger
from typing import Callable

from .. import Input, Output, Step
from ..models import Artifact, input_to_artifact
from ...project import Stage, Project
from ...steps import Meta, ArtifactType
from ...utilities.junit import TEST_OUTPUT_PATH_KEY, to_test_suites, sum_suites
from ...utilities.sbt import SbtConfig
from ...utilities.subprocess import custom_check_output


class TestSbt(Step):
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        super().__init__(
            logger=logger,
            meta=Meta(
                name='Sbt Test',
                description='Run sbt tests',
                version='0.0.1',
                stage=Stage.TEST
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE
        )

    def execute(self, step_input: Input) -> Output:
        with open(SbtConfig.java_opts_file_name, 'w+', encoding='utf-8') as jvm_opts:
            jvm_opts.write(SbtConfig.sbt_opts.replace(' ', '\n'))

            command_compile = self._construct_sbt_command(step_input, self._construct_sbt_command_compile)
            command_test = self._construct_sbt_command(step_input, self._construct_sbt_command_test)

            custom_check_output(self.logger, command_compile)
            output = custom_check_output(self.logger, command_test)
            project = step_input.project

            if output.success:
                artifact = self._extract_test_report(project, step_input)
                suite = to_test_suites(artifact)
                summary = sum_suites(suite)

                return Output(success=summary.is_success,
                              message=f"Tests results produced for {project.name} ({summary})",
                              produced_artifact=artifact)

            return Output(success=False,
                          message=f"Tests failed to run for {project.name}. No test results have been recorded.",
                          produced_artifact=None)

    @staticmethod
    def _construct_sbt_command_compile(step_input: Input) -> list[str]:
        return [
            f'project {step_input.project.name}',
            # 'coverageOn', # TODO: fix plugin definition?
            'test:compile'
        ]

    @staticmethod
    def _construct_sbt_command_test(step_input: Input):
        return [
            f'project {step_input.project.name}',
            'test',
            # 'coverageOff'
        ]

    @staticmethod
    def _construct_sbt_command(step_input: Input, commands_fn: Callable[[Input], list[str]]):
        command = SbtConfig.sbt_command.split(' ')
        command.append("; ".join(commands_fn(step_input)))
        return command

    @staticmethod
    def _extract_test_report(project: Project, step_input: Input) -> Artifact:
        return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                 spec={TEST_OUTPUT_PATH_KEY: f'{project.test_report_path}'})
