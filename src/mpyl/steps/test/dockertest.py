import os

from docker import DockerClient
from logging import Logger

from ..step import Step
from ..build import DockerConfig
from ..models import Meta, Input, Output, ArtifactType
from ...stage import Stage


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Docker Test',
            description='Docker test step',
            version='0.0.1',
            stage=Stage.TEST
        ), ArtifactType.DOCKER_IMAGE, ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")
        
        built_image = step_input.required_artifact
        if not built_image:
            self._logger.warn("After docker has image required artifact")
            return Output(success=False, message=f"After docker has image required artifact {step_input.project.name}")

        client = DockerClient.from_env()

        docker_config = DockerConfig(step_input.build_properties.config)
        image_name = built_image.spec['image']

        self._logger.info(f"Logging in with user '{docker_config.user_name}'")
        login_result = client.login(username=docker_config.user_name, password=docker_config.password,
                                    registry=f'https://{docker_config.host_name}')
        self._logger.debug(f"Docker login result: {login_result}")
        full_image_path = os.path.join(docker_config.host_name, image_name)

        #Run docker command --target test
        f"docker build -t {image_name} -f tests/projects/service/deployment/Dockerfile-mpl --build-arg " \
        f"'PROJECT_PATH=tests/projects/service' --build-arg 'TAG_NAME={docker_config.build_target}' --build-arg 'DOCKER_IMAGE={image_name}' --build-arg " \
        f"'MAINTAINER={maintainer}' '--target=tester' ."


        #Send output to test-reports 
        
        
        return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=None)
