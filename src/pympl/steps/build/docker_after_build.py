from logging import Logger
from pathlib import Path

import docker

from . import DockerConfig
from ..models import Meta, Input, Output, Artifact, ArtifactType
from ..step import Step
from ...stage import Stage


class AfterBuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='After Docker Build',
            description='Push docker image to registry',
            version='0.0.1',
            stage=Stage.BUILD
        ), ArtifactType.DOCKER_IMAGE, ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        built_image = step_input.required_artifact
        if not built_image:
            self._logger.warn("After docker has image required artifact")
            return Output(success=False, message=f"After docker has image required artifact {step_input.project.name}")

        client = docker.from_env()

        image_name = built_image.spec['image']
        self._logger.debug(f'Image to publish: {image_name}')

        docker_config = DockerConfig(step_input.build_properties.config)

        client.login(
            username=docker_config.user_name,
            password=docker_config.password,
            registry=docker_config.host_name
        )
        full_image_path = Path(docker_config.host_name, image_name)
        client.images.push(full_image_path)

        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.build_properties.git.revision, self.meta.name,
                            {'image': full_image_path})
        return Output(success=True, message=f"Pushed {full_image_path}", produced_artifact=artifact)
