"""Camunda cluster related docker commands to deploy diagrams"""

import os
import subprocess
from logging import Logger
from ....utilities.bpm import CamundaConfig


def deploy_diagram_to_cluster(logger: Logger, config: CamundaConfig):
    volume_path = os.path.join(os.getcwd(), config.deployment_path.bpm_project_path)
    bpm_file_path = config.deployment_path.bpm_diagram_folder_path

    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        logger.info(f"Deploying diagram: {file_name}")
        relative_file_path = os.path.relpath(
            os.path.join(bpm_file_path, file_name), volume_path
        )

        envs = {
            "ZEEBE_ADDRESS": config.zeebe_credentials.cluster_id,
            "ZEEBE_CLIENT_ID": config.zeebe_credentials.client_id,
            "ZEEBE_CLIENT_SECRET": config.zeebe_credentials.client_secret,
        }
        subprocess.run(["zbctl", "deploy", relative_file_path], env=envs, check=True)
