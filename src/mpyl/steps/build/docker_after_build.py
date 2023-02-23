""" Pushes the artifact created in the build stage to the docker registry for any build step that has
ArtifactType.DOCKER_IMAGE as `mpyl.steps.models.ArtifactType`."""

import os
from logging import Logger

from python_on_whales import docker

from ..models import Meta, Input, Output, Artifact, ArtifactType
from ..step import Step
from ...project import Stage
from ...utilities.docker import DockerConfig


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

        image_name = built_image.spec['image']
        self._logger.debug(f'Image to publish: {image_name}')

        docker_config = DockerConfig(step_input.run_properties.config)

        full_image_path = os.path.join(docker_config.host_name, image_name)
        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.run_properties.versioning.revision, self.meta.name,
                            {'image': full_image_path})

        if step_input.dry_run:
            return Output(success=True, message=f"Dry run. Not pushing {image_name} to {docker_config.host_name}",
                          produced_artifact=artifact)

        self._logger.info(f"Logging in with user '{docker_config.user_name}'")
        docker.login(server=f'https://{docker_config.host_name}', username=docker_config.user_name,
                     password=docker_config.password)
        image = docker.image.inspect(image_name)
        self._logger.debug(f'Found image {image}')
        docker.image.tag(image, full_image_path)

        docker.image.push(full_image_path, quiet=False)

        return Output(success=True, message=f"Pushed {full_image_path}", produced_artifact=artifact)
