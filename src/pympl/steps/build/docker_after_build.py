import os
from logging import Logger

from docker import DockerClient

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

        client = DockerClient.from_env()

        image_name = built_image.spec['image']
        self._logger.debug(f'Image to publish: {image_name}')

        docker_config = DockerConfig(step_input.build_properties.config)

        self._logger.info(f"Logging in with user '{docker_config.user_name}', {docker_config.password}")
        login_result = client.login(username=docker_config.user_name, password=docker_config.password,
                                    registry=f'https://{docker_config.host_name}')
        self._logger.debug(f"Docker login result: {login_result}")
        full_image_path = os.path.join(docker_config.host_name, image_name)
        tagged = client.images.get(image_name).tag(full_image_path)
        if tagged:
            stream = client.images.push(full_image_path, stream=True, decode=True)
            for line in stream:
                status = line.get('status')
                if status:
                    self._logger.info(status)
        else:
            return Output(success=False, message=f"Could not tag {full_image_path}")

        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.build_properties.versioning.revision, self.meta.name,
                            {'image': full_image_path})
        return Output(success=True, message=f"Pushed {full_image_path}", produced_artifact=artifact)
