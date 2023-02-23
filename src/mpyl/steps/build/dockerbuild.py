""" Step that builds a docker image from its specification in Dockerfile-mpl. """

from logging import Logger

from . import DockerConfig, build
from .docker_after_build import AfterBuildDocker
from ..models import Meta, Input, Output, ArtifactType, input_to_artifact
from ..step import Step
from ...project import Stage


class BuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Build',
            description='Build docker image',
            version='0.0.1',
            stage=Stage.BUILD
        ), produced_artifact=ArtifactType.DOCKER_IMAGE, required_artifact=ArtifactType.NONE,
                         after=AfterBuildDocker(logger=logger))

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig(step_input.run_properties.config)
        build_target = docker_config.test_target
        if not build_target:
            raise ValueError('docker.testTarget must be specified')

        success = build(logger=self._logger, step_input=step_input, target=build_target, config=docker_config)
        artifact = input_to_artifact(ArtifactType.DOCKER_IMAGE, step_input, {'image': step_input.docker_image_tag()})

        if success:
            return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=artifact)

        return Output(success=False, message=f"Failed to build docker image for {step_input.project.name}",
                      produced_artifact=None)
