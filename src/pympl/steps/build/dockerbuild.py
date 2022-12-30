from logging import Logger
from typing import Dict

from docker import APIClient  # type: ignore

from ..models import Meta, Input, Output, Artifact, ArtifactType
from ..step import Step
from ...stage import Stage


class DockerConfig:
    host_name: str
    user_name: str
    password: str

    def __init__(self, config: Dict):
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['host_name']
            self.user_name = registry['user_name']
            self.password = registry['password']
        except KeyError:
            raise KeyError(f'Docker config could not be loaded from {config}')


class BuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Docker Build',
            description='Build docker image and push to registry',
            version='0.0.1',
            stage=Stage.BUILD
        ), ArtifactType.DOCKER_IMAGE, ArtifactType.NONE)

    def __log_docker_output(self, generator, task_name: str = 'docker command execution') -> None:
        while True:
            try:
                output = generator.__next__()
                if 'stream' in output:
                    output_str = output['stream'].strip('\n')
                    self._logger.info(output_str)
            except StopIteration:
                self._logger.info(f'{task_name} complete.')
                break

    def execute(self, step_input: Input) -> Output:
        project = step_input.project
        self._logger.info(f"Building project {project.name}")
        low_level_client = APIClient()
        self._logger.debug(low_level_client.version())

        logs = low_level_client.build(path=project.deployment_path, dockerfile='Dockerfile-mpl',
                                      tag=step_input.docker_image_tag(),
                                      rm=True, target="installer", decode=True)
        self.__log_docker_output(logs)

        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.build_properties.git.revision, self.meta.name,
                            {'image': step_input.docker_image_tag()})
        return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=artifact)
