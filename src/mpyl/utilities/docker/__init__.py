"""Docker related utility methods"""

from logging import Logger
from typing import Dict, Optional

from python_on_whales import docker

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
            logger.info(str(output).strip('\n'))
        except StopIteration:
            logger.info(f'{task_name} complete.')
            break


def docker_image_tag(step_input: Input):
    git = step_input.run_properties.versioning
    tag = f"pr-{git.pr_number}" if git.pr_number else git.tag
    return f"{step_input.project.name.lower()}:{tag}".replace('/', '_')


def docker_file_path(project: Project, docker_config: DockerConfig):
    return f'{project.deployment_path}/{docker_config.docker_file_name}'


def build(logger: Logger, root_path: str, file_path: str, image_tag: str, target: str) -> bool:
    """
    :param logger: the logger
    :param root_path: the root path to which `docker_file_path` is relative
    :param file_path: path to the docker file to be built
    :param image_tag: the tag of the image
    :param target: the 'target' within the multi-stage docker image
    :return: True if success, False if failure
    """
    logger.info(f"Building docker image with {file_path}")

    logs = docker.buildx.build(context_path=root_path, file=file_path, tags=[image_tag], target=target,
                               stream_logs=True)
    __stream_docker_logging(logger, logs)
    logger.debug(logs)
    return True
