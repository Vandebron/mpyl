"""
Step implementations relating to the `Build` Stage. These steps produce Docker images by default
"""

from logging import Logger
from typing import Dict

from docker import APIClient  # type: ignore

from ..models import Input, Artifact, ArtifactType


class DockerConfig:
    host_name: str
    user_name: str
    password: str
    root_folder: str
    build_target: str
    test_target: str
    docker_file_name: str

    def __init__(self, config: Dict):
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['hostName']
            self.user_name = registry['userName']
            self.password = registry['password']
            build_config: dict = config['docker']['build']
            self.root_folder = build_config['rootFolder']
            self.build_target = build_config['buildTarget']
            self.docker_file_name = build_config['dockerFileName']

        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc


def __log_docker_output(logger: Logger, generator, task_name: str = 'docker command execution') -> None:
    while True:
        try:
            output = next(generator)
            if 'stream' in output:
                output_str = output['stream'].strip('\n')
                logger.info(output_str)
        except StopIteration:
            logger.info(f'{task_name} complete.')
            break


def build(logger: Logger, step_input: Input, artifact_type: ArtifactType, config: DockerConfig) -> Artifact:
    low_level_client = APIClient()
    logger.debug(low_level_client.version())
    logger.info(f"Running DockerClient with target {config.build_target} for project {step_input.project.name}")

    logs = low_level_client.build(path=config.root_folder,
                                  dockerfile=f'{step_input.project.deployment_path}/{config.docker_file_name}',
                                  tag=step_input.docker_image_tag(),
                                  rm=True, target=config.build_target, decode=True)
    __log_docker_output(logger, logs)
    logger.debug(logs)

    return Artifact(artifact_type, step_input.run_properties.versioning.revision, step_input.project.name,
                    {'image': step_input.docker_image_tag()})
