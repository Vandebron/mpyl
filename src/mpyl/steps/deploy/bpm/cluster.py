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
        logger.info(f"Deploying diagram: {file_name}")
        relative_file_path = os.path.relpath(
            os.path.join(bpm_file_path, file_name), volume_path
        )

        command = f"zbctl deploy {relative_file_path}"

        environment_variables = {
            "ZEEBE_ADDRESS": config.zeebe_credentials.cluster_id,
            "ZEEBE_CLIENT_ID": config.zeebe_credentials.client_id,
            "ZEEBE_CLIENT_SECRET": config.zeebe_credentials.client_secret,
        }

        custom_check_output(logger, command, environment_variables=environment_variables)
