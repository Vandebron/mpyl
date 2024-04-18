"""Camunda cluster related docker commands to deploy diagrams"""

import os
from logging import Logger
from python_on_whales import docker, Container, DockerException
from ....utilities.bpm import CamundaConfig
from ....utilities.docker import execute_with_stream


def deploy_diagram_to_cluster(logger: Logger, config: CamundaConfig, docker_container):
    volume_path = os.path.join(os.getcwd(), config.depolyment_path.bpm_project_path)
    bpm_file_path = config.depolyment_path.bpm_diagram_folder_path
    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        logger.info(f"Deploying diagram: {file_name}")
        relative_file_path = os.path.relpath(
            os.path.join(bpm_file_path, file_name), volume_path
        )
        run_command = f"zbctl deploy {relative_file_path}"
        result = execute_with_stream(
            logger=logger,
            container=docker_container,
            command=run_command,
            task_name=f"Deploy bpmn diagram {file_name}",
        )
        for stdout in result:
            if "error Command failed with exit code" in stdout:
                raise DockerException(command_launched=[run_command], return_code=1)


def get_docker_container(config: CamundaConfig) -> Container:
    volume_path = os.path.join(os.getcwd(), config.depolyment_path.bpm_project_path)
    custom_image_tag = "mpyl/bpmn"
    docker.build(
        context_path=volume_path,
        tags=[custom_image_tag],
        file=f"{volume_path}{config.depolyment_path.docker_file_path}",
    )

    docker_container = docker.run(
        image=custom_image_tag,
        interactive=True,
        detach=True,
        volumes=[(volume_path, config.depolyment_path.docker_directory_path)],
        envs={
            "ZEEBE_ADDRESS": config.zeebe_credentials.cluster_id,
            "ZEEBE_CLIENT_ID": config.zeebe_credentials.client_id,
            "ZEEBE_CLIENT_SECRET": config.zeebe_credentials.client_secret,
        },
        workdir=config.depolyment_path.docker_directory_path,
    )
    if not isinstance(docker_container, Container):
        raise TypeError("Docker run command should return a container")

    return docker_container
