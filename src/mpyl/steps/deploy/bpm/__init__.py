"""Bpm deployment related helper methods"""

from logging import Logger
import os

from ....utilities.subprocess import custom_check_output
from ..bpm.camunda_modeler_client import CamundaModelerClient
from ..bpm.modeler import deploy_diagram_to_modeler
from ....utilities.bpm import CamundaConfig
from ....utilities.http_client.exceptions import HTTPRequestError, AuthorizationError
from ...models import Output


def deploy_to_cluster(
    logger: Logger, project_name: str, config: CamundaConfig
) -> Output:
    bpm_file_path = config.deployment_path.bpm_diagram_folder_path

    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        relative_file_path = os.path.join(bpm_file_path, file_name)

        logger.info(f"Deploying {relative_file_path}")

        command = (
            f"zbctl deploy {relative_file_path} "
            f"--address {config.zeebe_credentials.cluster_id} "
            f"--clientId {config.zeebe_credentials.client_id} "
            f"--clientSecret {config.zeebe_credentials.client_secret}"
        )

        output = custom_check_output(logger, command)

        if not output.success:
            return Output(
                success=False,
                message=(
                    f"Deployment of BPM diagrams to cluster for project {project_name} "
                    f"failed with {output.message}"
                ),
                produced_artifact=None,
            )

    return Output(
        success=True,
        message=f"Deployed all diagrams in {project_name} to Camunda cluster",
        produced_artifact=None,
    )


def deploy_to_modeler(
    logger: Logger, project_name: str, config: CamundaConfig
) -> Output:
    credentials = config.modeler_credentials.to_dict()
    camunda_client = CamundaModelerClient(
        config.modeler_api.base_url,
        config.modeler_api.token_url,
        credentials,
    )
    bpm_file_path = config.deployment_path.bpm_diagram_folder_path
    pr_number = config.pr_number
    try:
        deploy_diagram_to_modeler(
            logger, bpm_file_path, config, camunda_client, pr_number
        )
    except AuthorizationError:
        return Output(
            success=False,
            message=f"Authorization Error for project {project_name}",
            produced_artifact=None,
        )
    except HTTPRequestError as err:
        return Output(
            success=False,
            message=f"Deploy BPMN diagrams to modeler for project {project_name} have http error {err}",
            produced_artifact=None,
        )
    except ValueError as err:
        return Output(
            success=False,
            message=f"Project {project_name} has value error: {err}",
            produced_artifact=None,
        )

    return Output(
        success=True,
        message=f"Deployed all diagrams in {project_name} to Camunda modeler",
        produced_artifact=None,
    )
