"""Docker related utility methods"""

from logging import Logger
from typing import Dict, Optional

from docker import APIClient  # type: ignore
from docker.errors import APIError

from ...project import Project
from ...steps.models import Input


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


def docker_image_tag(step_input: Input):
    git = step_input.run_properties.versioning
    tag = f"pr-{git.pr_number}" if git.pr_number else git.tag
    return f"{step_input.project.name.lower()}:{tag}".replace('/', '_')


def docker_file_path(project: Project, docker_config: DockerConfig):
    return f'{project.deployment_path}/{docker_config.docker_file_name}'


def build(logger: Logger, docker_client: APIClient, root_path: str, file_path: str, image_tag: str,
          target: str) -> bool:
    """
    :param logger: the logger
    :param docker_client: the docker API client
    :param root_path: the root path to which `docker_file_path` is relative
    :param file_path: path to the docker file to be built
    :param image_tag: the tag of the image
    :param target: the 'target' within the multi-stage docker image
    :return: True if success, False if failure
    """
    logger.debug(docker_client.version())
    summary = f"target '{target}' for {docker_file_path}"
    logger.info(f"Building docker image with {file_path}")

    try:
        logs = docker_client.build(path=root_path, dockerfile=file_path, tag=image_tag, rm=True, target=target,
                                   decode=True)
        __stream_docker_logging(logger, logs)
        logger.debug(logs)
    except APIError:
        logger.warning(f'Error while building {summary}', exc_info=True)
        return False
    return True
