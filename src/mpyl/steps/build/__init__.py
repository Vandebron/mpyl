"""
Step implementations relating to the `Build` Stage. These steps produce Docker images by default
"""

from logging import Logger
from typing import Dict, Optional

from docker import APIClient  # type: ignore
from docker.errors import APIError

from ..models import Input, Artifact, ArtifactType


class DockerConfig:
    host_name: str
    user_name: str
    password: str
    root_folder: str
    build_target: Optional[str]
    test_target: Optional[str]
    docker_file_name: str

    def __init__(self, config: Dict):
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['hostName']
            self.user_name = registry['userName']
            self.password = registry['password']
            build_config: dict = config['docker']['build']
            self.root_folder = build_config['rootFolder']
            self.build_target = build_config.get('buildTarget', None)
            self.test_target = build_config.get('testTarget', None)
            self.docker_file_name = build_config['dockerFileName']

        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc


def __stream_docker_logging(logger: Logger, generator, task_name: str = 'docker command execution') -> None:
    while True:
        try:
            output = next(generator)
            if 'stream' in output:
                output_str = output['stream'].strip('\n')
                logger.info(output_str)
        except StopIteration:
            logger.info(f'{task_name} complete.')
            break


def build(logger: Logger, step_input: Input, target: str, config: DockerConfig) -> bool:
    """
    :param logger: the logger
    :param step_input: information about the image that should be built
    :param target: the 'target' within the multi-stage docker image
    :param config: global docker configuration
    :return: True if success, False if failure
    """
    low_level_client = APIClient()
    logger.debug(low_level_client.version())
    summary = f"target '{target}' for project {step_input.project.name}"
    logger.info(f"Building docker image with {summary}")

    try:
        logs = low_level_client.build(path=config.root_folder,
                                      dockerfile=f'{step_input.project.deployment_path}/{config.docker_file_name}',
                                      tag=step_input.docker_image_tag(),
                                      rm=True, target=target, decode=True)
        __stream_docker_logging(logger, logs)
        logger.debug(logs)
    except APIError:
        logger.warning(f'Error while building {summary}', exc_info=True)
        return False
    return True
