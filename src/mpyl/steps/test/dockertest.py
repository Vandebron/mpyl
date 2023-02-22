""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """

from logging import Logger
from docker import APIClient  # type: ignore

from ..step import Step
from ..build import DockerConfig
from ..models import Meta, Input, Output, ArtifactType, Artifact
from ...project import Stage


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Test',
            description='Test docker image',
            version='0.0.1',
            stage=Stage.TEST
        ), produced_artifact=ArtifactType.DOCKER_IMAGE, required_artifact=ArtifactType.NONE)

    def __log_docker_output(self, generator, task_name: str = 'docker command execution') -> None:
        while True:
            try:
                output = next(generator)
                if 'stream' in output:
                    output_str = output['stream'].strip('\n')
                    self._logger.info(output_str)
            except StopIteration:
                self._logger.info(f'{task_name} complete.')
                break

    def execute(self, step_input: Input) -> Output:
        project = step_input.project
        self._logger.info(f"Testing project {project.name}")
        low_level_client = APIClient()
        self._logger.debug(low_level_client.version())

        docker_config = DockerConfig(step_input.run_properties.config)

        logs = low_level_client.build(path=docker_config.root_folder,
                                      dockerfile=f'{project.deployment_path}/{docker_config.docker_file_name}',
                                      tag=step_input.docker_image_tag(),
                                      rm=True, target="tester", decode=True)
        self.__log_docker_output(logs)
        self._logger.debug(logs)

        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.run_properties.versioning.revision, self.meta.name,
                            {'image': step_input.docker_image_tag()})
        return Output(success=True, message=f"Tested {step_input.project.name}", produced_artifact=artifact)
