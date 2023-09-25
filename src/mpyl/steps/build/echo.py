""" Dummy build step to test the framework. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact
from . import STAGE_NAME
from ...utilities.docker import docker_image_tag, DockerImageSpec


class BuildEcho(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Echo Build",
                description="Dummy build step to test the framework",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Building project {step_input.project.name}")
        artifact = input_to_artifact(
            ArtifactType.DOCKER_IMAGE,
            step_input,
            spec=DockerImageSpec(docker_image_tag(step_input)),
        )
        return Output(
            success=True,
            message=f"Built {step_input.project.name}",
            produced_artifact=artifact,
        )
