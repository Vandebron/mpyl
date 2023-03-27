""" Step that deploys ephemeral the docker images produced in the build stage """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage
from ...utilities.docker import docker_image_tag, write_env_to_file
from ...utilities.subprocess import custom_check_output


class Ephemeral(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Ephemeral Deploy',
            description='Deploy ephemeral container',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        env_file_name = write_env_to_file(step_input.project, step_input.run_properties)
        docker_image_name = docker_image_tag(step_input)

        return custom_check_output(self._logger,
                                   f"docker run --rm --env-file ${env_file_name} ${docker_image_name}")
