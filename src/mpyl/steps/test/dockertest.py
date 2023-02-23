""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """

from logging import Logger

from ..build import DockerConfig, build
from ..models import Meta, Input, Output, ArtifactType, input_to_artifact
from ..step import Step
from ...project import Stage


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Test',
            description='Test docker image',
            version='0.0.1',
            stage=Stage.TEST
        ), produced_artifact=ArtifactType.JUNIT_TESTS, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig(step_input.run_properties.config)
        test_target = docker_config.test_target
        if not test_target:
            raise ValueError('docker.testTarget must be specified')

        success = build(logger=self._logger, step_input=step_input, target=test_target, config=docker_config)

        artifact = input_to_artifact(ArtifactType.JUNIT_TESTS, step_input, {'test_path': step_input.docker_image_tag()})
        if success:
            return Output(success=True, message=f"Tests succeeded for {step_input.project.name}",
                          produced_artifact=artifact)

        return Output(success=False, message=f"Test failure in {step_input.project.name}", produced_artifact=artifact)
