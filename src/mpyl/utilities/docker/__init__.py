"""Docker related utility methods"""
import logging
import shlex
import shutil
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from traceback import print_exc
from typing import Dict, Optional, Iterator, cast, Union
from python_on_whales import docker, Image, Container, DockerException
from python_on_whales.exceptions import NoSuchContainer
from ruamel.yaml import yaml_object, YAML

from ..logging import try_parse_ansi
from ...project import Project
from ...steps.models import Input, ArtifactSpec

yaml = YAML()


@yaml_object(yaml)
@dataclass
class DockerImageSpec(ArtifactSpec):
    yaml_tag = "!DockerImageSpec"
    image: str


@dataclass(frozen=True)
class DockerComposeConfig:
    period_seconds: int
    failure_threshold: int

    @property
    def total_duration(self):
        return self.period_seconds * self.failure_threshold

    @staticmethod
    def from_yaml(config: dict):
        compose_config = config.get("docker", {}).get("compose")
        if not compose_config:
            raise KeyError("docker.compose needs to be defined")
        return DockerComposeConfig(
            period_seconds=int(compose_config["periodSeconds"]),
            failure_threshold=int(compose_config["failureThreshold"]),
        )


@dataclass(frozen=True)
class DockerCacheConfig:
    cache_to: str
    cache_from: str

    @staticmethod
    def from_dict(config: Dict):
        return DockerCacheConfig(config["to"], config["from"])


@dataclass(frozen=True)
class DockerRegistryConfig:
    host_name: str
    organization: Optional[str]
    user_name: str
    password: str
    cache_from_registry: bool
    custom_cache_config: Optional[DockerCacheConfig]

    @staticmethod
    def from_dict(config: dict):
        try:
            cache_config = config.get("cache", {})
            return DockerRegistryConfig(
                host_name=config["hostName"],
                user_name=config["userName"],
                organization=config.get("organization", None),
                password=config["password"],
                cache_from_registry=cache_config.get("cacheFromRegistry", False),
                custom_cache_config=DockerCacheConfig.from_dict(cache_config["custom"])
                if "custom" in cache_config
                else None,
            )
        except KeyError as exc:
            raise KeyError(f"Docker config could not be loaded from {config}") from exc


@dataclass(frozen=True)
class DockerConfig:
    default_registry: str
    registries: list[DockerRegistryConfig]
    root_folder: str
    build_target: Optional[str]
    test_target: Optional[str]
    docker_file_name: str

    @staticmethod
    def from_dict(config: dict):
        try:
            registries: dict = config["docker"]["registries"]
            build_config: dict = config["docker"]["build"]
            return DockerConfig(
                default_registry=config["docker"]["defaultRegistry"],
                registries=[DockerRegistryConfig.from_dict(r) for r in registries],
                root_folder=build_config["rootFolder"],
                build_target=build_config.get("buildTarget", None),
                test_target=build_config.get("testTarget", None),
                docker_file_name=build_config["dockerFileName"],
            )
        except KeyError as exc:
            raise KeyError(f"Docker config could not be loaded from {config}") from exc


def execute_with_stream(
    logger: Logger,
    container: Container,
    command: str,
    task_name: str,
    multiprocess: bool = False,
):
    if multiprocess:  # Logger settings need to be re-applied in each process
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

    result = cast(
        Iterator[tuple[str, bytes]],
        container.execute(command=shlex.split(command), stream=True),
    )
    result_list = stream_docker_logging(logger, result, task_name)

    logger.handlers.clear()

    return result_list


def stream_docker_logging(
    logger: Logger,
    generator: Union[Iterator[str], Iterator[tuple[str, bytes]]],
    task_name: str,
    level=logging.INFO,
) -> list[str]:
    copied_logs = []

    while True:
        try:
            next_item = next(generator)
            log_line = (
                next_item[1].decode(errors="replace")
                if isinstance(next_item, tuple)
                else next_item
            )
            copied_logs.append(log_line)
            logger.log(level, try_parse_ansi(log_line))
        except StopIteration:
            logger.info(f"{task_name} complete.")
            return copied_logs


def docker_image_tag(step_input: Input) -> str:
    git = step_input.run_properties.versioning
    tag = git.tag if git.tag else f"pr-{git.pr_number}"
    return f"{step_input.project.name.lower()}:{tag}".replace("/", "_")


def get_default_build_args(
    image_tag: str, maintainers: list[str], tag_name: str
) -> dict[str, str]:
    return {
        "DOCKER_IMAGE": image_tag,
        "MAINTAINER": ",".join(maintainers),
        "TAG_NAME": tag_name,
    }


def docker_registry_path(docker_config: DockerRegistryConfig, image_name: str) -> str:
    path_components = [
        docker_config.host_name,
        docker_config.organization,
        image_name,
    ]
    return "/".join([c for c in path_components if c]).lower()


def full_image_path_for_project(step_input: Input) -> str:
    docker_config: DockerConfig = DockerConfig.from_dict(
        step_input.run_properties.config
    )
    docker_registry = registry_for_project(docker_config, step_input.project)

    image_name = docker_image_tag(step_input)
    return (
        docker_registry_path(docker_registry, image_name)
        if not step_input.dry_run
        else image_name
    )


def push_to_registry(
    logger: Logger, docker_config: DockerRegistryConfig, image_name: str
):
    image = docker.image.inspect(image_name)
    logger.debug(f"Found image {image}")

    login(logger=logger, registry_config=docker_config)
    full_image_path = docker_registry_path(docker_config, image_name)
    docker.image.tag(image, full_image_path)
    docker.image.push(full_image_path, quiet=False)


def registry_for_project(
    docker_config: DockerConfig, project: Project
) -> DockerRegistryConfig:
    host_name = (
        project.docker.host_name if project.docker else docker_config.default_registry
    )
    registry = next(r for r in docker_config.registries if r.host_name == host_name)
    if registry:
        return registry

    raise KeyError(f"Docker config has no registry with host name {host_name}")


def docker_file_path(project: Project, docker_config: DockerConfig):
    return f"{project.deployment_path}/{docker_config.docker_file_name}"


def docker_copy(
    logger: Logger, container_path: str, dst_path: str, container: Container
):
    """
    Copies the contents of the specified path within the container to a locally created destination

    :param logger: the logger
    :param container_path: the path of the directory in the container to copy
    :param dst_path: the path to copy the container content to
    :param container: the container to copy from
    """
    shutil.rmtree(dst_path, ignore_errors=True)
    Path(dst_path).mkdir(parents=True, exist_ok=True)

    if not docker.container.exists(container.id):
        raise ValueError(f"Container {container.id} does not exist")

    logger.info(
        f"Copying contents from container {container.id} at "
        f"path {container_path} to host at {dst_path}"
    )
    try:
        docker.copy(f"{container.id}:{container_path}", dst_path)
    except NoSuchContainer as exc:
        logger.warning(
            f"Could not find data in container {container.name} at expected location {container_path}"
        )
        raise exc


def build(
    logger: Logger,
    root_path: str,
    file_path: str,
    image_tag: str,
    target: str,
    build_args: dict[str, str],
    registry_config: Optional[DockerRegistryConfig] = None,
) -> bool:
    """
    :param logger: the logger
    :param root_path: the root path to which `docker_file_path` is relative
    :param file_path: path to the docker file to be built
    :param image_tag: the tag of the image
    :param target: the 'target' within the multi-stage docker image
    :param registry_config: optional docker config, used what type of cache to use if any
    :param build_args: build arguments to supply to docker build
    :return: True for success, False for failure
    """
    logger.info(f"Building docker image with {file_path} and target {target}")

    if registry_config and registry_config.cache_from_registry:
        registry_path = docker_registry_path(registry_config, image_tag)
        cache_from = f"type=registry,ref={registry_path}"
        cache_to = "type=inline"
    elif registry_config and registry_config.custom_cache_config:
        cache_from = registry_config.custom_cache_config.cache_from
        cache_to = registry_config.custom_cache_config.cache_to
    else:
        cache_from = None
        cache_to = None

    logger.debug(f"Building with cache from: {cache_from} {registry_config}")

    try:
        logs = docker.buildx.build(
            context_path=root_path,
            file=file_path,
            tags=[image_tag],
            target=target,
            stream_logs=True,
            cache_from=cache_from,
            cache_to=cache_to,
            build_args=build_args if build_args else {},
        )
        if logs is not None and not isinstance(logs, Image):
            stream_docker_logging(
                logger=logger, generator=logs, task_name=f"Build {file_path}:{target}"
            )
        logger.debug(logs)
        return True

    except DockerException as exc:
        command = " ".join(exc.docker_command)
        logger.warning(
            f"Docker build failed with command {command} and exit code {exc.return_code}"
        )
        return False
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Docker build failed with {exc.__class__.__name__}")
        print_exc()
        return False


def login(logger: Logger, registry_config: DockerRegistryConfig) -> None:
    logger.info(f"Logging in with user '{registry_config.user_name}'")
    docker.login(
        server=f"https://{registry_config.host_name}",
        username=registry_config.user_name,
        password=registry_config.password,
    )
    logger.debug(f"Logged in as '{registry_config.user_name}'")


def create_container(logger: Logger, image_name: str) -> Container:
    logger.debug(f"Creating container from image {image_name}")
    container = docker.create(image_name)
    logger.info(f"Created container {container.id} from image {image_name}")
    return container


def remove_container(logger: Logger, container: Container) -> None:
    logger.debug(f"Removing container {container.id}")
    docker.remove(container.id)
    logger.info(f"Removed container {container.id}")
