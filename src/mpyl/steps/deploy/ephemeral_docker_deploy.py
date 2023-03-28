""" Step that deploys ephemeral the docker images produced in the build stage """

from logging import Logger

from python_on_whales import docker

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage
from ...utilities.docker import docker_image_tag, get_env_variables


class EphemeralDockerDeploy(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Ephemeral Docker Deploy',
            description='Deploy From Docker Container',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        env_variables = get_env_variables(step_input.project, step_input.run_properties)
        docker_image_name = docker_image_tag(step_input)
        docker_run_result = docker.run(image=docker_image_name, remove=True, envs=env_variables)
        self._logger.info(docker_run_result)

        return Output(success=True, message=f"Deployed project {step_input.project.name}", produced_artifact=None)
