"""
Step implementations relating to the `Build` Stage. These steps produce Docker images by default
"""

from logging import Logger
from typing import Dict

from docker import APIClient  # type: ignore

from ..models import Input, Artifact


class DockerConfig:
    host_name: str
    user_name: str
    password: str
    root_folder: str
    build_target: str
    test_target: str
    docker_file_name: str

    def __init__(self, config: Dict, logger: Logger):
        self._logger = logger
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['hostName']
            self.user_name = registry['userName']
            self.password = registry['password']
            build: dict = config['docker']['build']
            self.root_folder = build['rootFolder']
            self.build_target = build['buildTarget']
            self.docker_file_name = build['dockerFileName']

        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc

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

    def build(self, step_input: Input, artifact_type) -> Artifact:
        low_level_client = APIClient()
        self._logger.debug(low_level_client.version())
        self._logger.info(f"Running DockerClient with target {self.build_target} for project {step_input.project.name}")

        logs = low_level_client.build(path=self.root_folder,
                                      dockerfile=f'{step_input.project.deployment_path}/{self.docker_file_name}',
                                      tag=step_input.docker_image_tag(),
                                      rm=True, target=self.build_target, decode=True)
        self.__log_docker_output(logs)
        self._logger.debug(logs)

        return Artifact(artifact_type, step_input.run_properties.versioning.revision, step_input.project.name,
                        {'image': step_input.docker_image_tag()})
