"""A step to compile and run tests for an SBT project"""
from logging import Logger
from typing import cast

from . import STAGE_NAME
from .after_test import IntegrationTestAfter
from .before_test import IntegrationTestBefore
from .. import Input, Output, Step
from ..models import Artifact, input_to_artifact
from ...project import Project
from ...steps import Meta, ArtifactType
from ...utilities.junit import (
    to_test_suites,
    sum_suites,
    JunitTestSpec,
)
from ...utilities.sbt import SbtConfig
from ...utilities.subprocess import custom_check_output


class TestSbt(Step):
    __test__ = False

    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Sbt Test",
                description="Run sbt tests",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
            before=IntegrationTestBefore(logger),
            after=IntegrationTestAfter(logger),
        )

    def _test(self, step_input: Input, sbt_config: SbtConfig) -> Output:
        command_compile = self._construct_sbt_command(
            project_name=step_input.project_execution.name,
            config=sbt_config,
            compile_test=True,
        )
        compile_outcome = custom_check_output(
            logger=self._logger, command=command_compile, use_print=True
        )
        if not compile_outcome.success:
            if sbt_config.test_with_coverage:
                coverage_off_command = sbt_config.to_command(
                    sbt_config.test_with_client, ["coverageOff"]
                )
                custom_check_output(
                    logger=self._logger, command=coverage_off_command, use_print=True
                )
            return Output(
                success=False,
                message=f"Tests failed to compile for {step_input.project_execution.name}",
                produced_artifact=None,
            )

        command_test = self._construct_sbt_command(
            project_name=step_input.project_execution.name,
            config=sbt_config,
            compile_test=False,
        )
        run_outcome = custom_check_output(
            logger=self._logger, command=command_test, use_print=True
        )
        artifact = self._extract_test_report(
            step_input.project_execution.project, step_input
        )
        if not run_outcome.success:
            return Output(
                success=False,
                message=f"Tests without coverage failed to run for {step_input.project_execution.name}",
                produced_artifact=artifact,
            )
        return Output(success=True, message="Success", produced_artifact=artifact)

    def execute(self, step_input: Input) -> Output:
        project = step_input.project_execution
        sbt_config = SbtConfig.from_config(config=step_input.run_properties.config)
        self._logger.debug(f"Config {sbt_config}")
        test_result = self._test(step_input=step_input, sbt_config=sbt_config)

        if test_result.produced_artifact:
            suite = to_test_suites(
                cast(JunitTestSpec, test_result.produced_artifact.spec)
            )
            summary = sum_suites(suite)
            return Output(
                success=summary.is_success,
                message=f"Tests results produced for {project.name} ({summary})",
                produced_artifact=test_result.produced_artifact,
            )

        return test_result

    @staticmethod
    def _construct_sbt_command(
        project_name: str, config: SbtConfig, compile_test: bool
    ):
        command = list(
            filter(
                None,
                [
                    f"project {project_name}",
                    "coverageOn" if config.test_with_coverage else None,
                    f"test{':compile' if compile_test else ''}",
                    "coverageOff" if config.test_with_coverage else None,
                ],
            )
        )
        return config.to_command(config.test_with_client, command)

    @staticmethod
    def _extract_test_report(project: Project, step_input: Input) -> Artifact:
        return input_to_artifact(
            artifact_type=ArtifactType.JUNIT_TESTS,
            step_input=step_input,
            spec=JunitTestSpec(
                f"{project.test_report_path}",
                step_input.run_properties.details.tests_url,
            ),
        )
