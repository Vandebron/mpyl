""" Step that runs relevant cypress tests in the post deploy stage """

import os

from logging import Logger
from typing import cast

from python_on_whales import docker, Container

from .. import Step, Meta
from ..models import ArtifactType, Input, Output
from ...project import Stage
from ...utilities.docker import execute_with_stream, stream_encoded_logging


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

        cypress_config = step_input.run_properties.config['cypress']
        volume_path = os.path.join('.', cypress_config['volumePath'])
        if os.getcwd().endswith('tests'):
            volume_path = './test_resources/cypress'

        specs_string = ''
        if step_input.project.dependencies and step_input.project.dependencies.postdeploy:
            specs_string = ', '.join(step_input.project.dependencies.postdeploy)

        docker_container = cast(Container, docker.run(image="cypress/browsers:latest", interactive=True, detach=True,
                                                          volumes=[(volume_path, "/cypress")], workdir="/cypress"))
        try:
            install_stream = execute_with_stream(container=docker_container, command=["yarn", "cypress", "install"])
            stream_encoded_logging(self._logger, install_stream, "Installing cypress")
            verify_stream = execute_with_stream(container=docker_container, command=["yarn", "cypress", "verify"])
            stream_encoded_logging(self._logger, verify_stream, "Verifying cypress")

            run_command = ["yarn", "cypress", "run", "--spec", f'{specs_string}']
            record_key = cypress_config['recordKey']
            if not step_input.run_properties.local and record_key:
                run_command.extend(["--record", "--key", cypress_config['recordKey']])
            test_result_stream = execute_with_stream(container=docker_container, command=run_command)
            stream_encoded_logging(logger=self._logger, generator=test_result_stream,
                                           task_name="Running cypress tests")
        finally:
            docker_container.stop()
            docker_container.remove()

        return Output(success=True, message=f"Cypress tests for {step_input.project.name} passed",
                        produced_artifact=None)
