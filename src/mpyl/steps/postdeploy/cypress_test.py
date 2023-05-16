import os

from logging import Logger
from typing import cast

from python_on_whales import docker, Container

from .. import Step, Meta
from ..models import ArtifactType, Input, Output
from ...project import Stage
from ...utilities.docker import decode_and_stream_execute_logs


class CypressTest(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Cypress Test',
            description='Step to run cypress tests',
            version='0.0.1',
            stage=Stage.POST_DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Running cypress tests for project {step_input.project.name}")

        # TODO: get volume location and spec files based on step_input?
        docker_container = cast(Container, docker.run(image="cypress/browsers:latest", interactive=True, detach=True,
                                      volumes=[(f"{os.getcwd()}/test_resources/cypress", "/cypress")],
                                      workdir="/cypress"))
        install_stream = docker_container.execute(command=["yarn", "cypress", "install"], stream=True)
        decode_and_stream_execute_logs(self._logger, install_stream, "Installing cypress")
        decode_and_stream_execute_logs(self._logger, '########## this should be printed $$$$$$$$$$', "Testing")
        verify_stream = docker_container.execute(command=["yarn", "cypress", "verify"], stream=True)
        decode_and_stream_execute_logs(self._logger, verify_stream, "Verifying cypress")
        output = Output(success=True, message=f"Cypress tests for {step_input.project.name} passed",
                        produced_artifact=None)

        try:
            run_command = ["yarn", "test"]
            if not step_input.run_properties.local:
                run_command.extend(["--record", "--key", step_input.run_properties.config['cypress']['recordKey']])
            test_result_stream = docker_container.execute(command=run_command, stream=True)
            decode_and_stream_execute_logs(logger=self._logger, generator=test_result_stream, task_name="Running cypress tests")
        except Exception as exc:  # pylint: disable=broad-except
            output = Output(success=False,
                            message=f"Cypress tests for {step_input.project.name} failed with exception: \n{exc}",
                            produced_artifact=None)

        docker_container.stop()
        docker_container.remove()

        return output
