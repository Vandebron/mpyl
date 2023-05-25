""" Step that runs relevant cypress tests in the post deploy stage """

import os

from logging import Logger

from python_on_whales import docker, Container

from .. import Step, Meta
from ..models import ArtifactType, Input, Output
from ...project import Stage
from ...utilities.cypress import CypressConfig
from ...utilities.docker import execute_with_stream


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

        cypress_config = CypressConfig.from_config(step_input.run_properties.config)
        volume_path = os.path.join(os.getcwd(), cypress_config.cypress_source_code_path)

        if step_input.project.dependencies and step_input.project.dependencies.postdeploy:
            specs_string = ', '.join(step_input.project.dependencies.postdeploy)
        else:
            raise ValueError("No cypress specs are defined in the project dependencies")

        docker_container = docker.run(image="cypress/browsers:latest", interactive=True, detach=True,
                                      volumes=[(volume_path, "/cypress")], workdir="/cypress")
        if not isinstance(docker_container, Container):
            raise TypeError("Docker run command should return a container")

        try:
            execute_with_stream(logger=self._logger, container=docker_container, command="yarn install",
                                task_name="Installing cypress")
            execute_with_stream(logger=self._logger, container=docker_container, command="yarn cypress install",
                                task_name="Installing cypress")
            execute_with_stream(logger=self._logger, container=docker_container, command="yarn cypress verify",
                                task_name="Verifying cypress")

            run_command = f"yarn cypress run --spec {specs_string}"
            record_key = cypress_config.record_key
            if not step_input.run_properties.local and record_key:
                run_command += f" --record --key {record_key}"
            execute_with_stream(logger=self._logger, container=docker_container, command=run_command,
                                task_name="Running cypress tests")
        finally:
            docker_container.stop()
            docker_container.remove()

        return Output(success=True, message=f"Cypress tests for {step_input.project.name} passed",
                      produced_artifact=None)
