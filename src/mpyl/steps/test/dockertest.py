""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """

from logging import Logger

from ..build import DockerConfig
from ..models import Meta, Input, Output, ArtifactType
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
        docker_config = DockerConfig(step_input.run_properties.config, self._logger)
        artifact = DockerConfig.build(docker_config, step_input, self.produced_artifact)
        return Output(success=True, message=f"Tested {step_input.project.name}", produced_artifact=artifact)
