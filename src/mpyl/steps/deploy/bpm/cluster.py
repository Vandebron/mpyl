"""Camunda cluster related docker commands to deploy diagrams"""

import os
from logging import Logger
from ....utilities.bpm import CamundaConfig
from ....utilities.subprocess import custom_check_output


def deploy_diagram_to_cluster(logger: Logger, config: CamundaConfig):
    volume_path = os.path.join(os.getcwd(), config.deployment_path.bpm_project_path)
    bpm_file_path = config.deployment_path.bpm_diagram_folder_path

    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        logger.info(f"Deploying {file_name}")
        logger.info(f"Volume path: {volume_path}")
        logger.info(f"BPM file path: {bpm_file_path}")
        relative_file_path = os.path.join(volume_path, bpm_file_path, file_name)

        logger.info(f"Deploying {relative_file_path}")

        command = (
            f"zbctl deploy {relative_file_path} "
            "--address {config.zeebe_credentials.cluster_id} "
            "--clientId {config.zeebe_credentials.client_id} "
            "--clientSecret {config.zeebe_credentials.client_secret}"
        )

        custom_check_output(logger, command)
