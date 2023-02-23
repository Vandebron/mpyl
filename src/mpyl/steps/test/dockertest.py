""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """

from logging import Logger

from ..models import Meta, Input, Output, ArtifactType, input_to_artifact
from ..step import Step
from ...docker import DockerConfig, build, docker_image_tag, docker_file_path
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

        tag = docker_image_tag(step_input) + '-test'
        dockerfile = docker_file_path(project=step_input.project, docker_config=docker_config)

        success = build(logger=self._logger, root_path=docker_config.root_folder, file_path=dockerfile, image_tag=tag,
                        target=test_target)

        artifact = input_to_artifact(ArtifactType.JUNIT_TESTS, step_input, {'test_path': 'test-path'})
        if success:
            return Output(success=True, message=f"Tests succeeded for {step_input.project.name}",
                          produced_artifact=artifact)

        return Output(success=False, message=f"Test failure in {step_input.project.name}", produced_artifact=artifact)
