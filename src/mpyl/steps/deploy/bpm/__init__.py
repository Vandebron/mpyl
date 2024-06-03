"""Bpm deployment related helper methods"""

from logging import Logger
from python_on_whales import DockerException
from ..bpm.camunda_modeler_client import CamundaModelerClient
from ..bpm.cluster import deploy_diagram_to_cluster, get_docker_container
from ..bpm.modeler import deploy_diagram_to_modeler
from ....utilities.bpm import CamundaConfig
from ....utilities.http_client.exceptions import HTTPRequestError, AuthorizationError
from ...models import Output


def deploy_to_cluster(
    logger: Logger, project_name: str, config: CamundaConfig
) -> Output:
    docker_container = get_docker_container(config)
    try:
        deploy_diagram_to_cluster(logger, config, docker_container)
    except DockerException:
        return Output(
            success=False,
            message=f"Deploy BPMN diagrams to cluster for project {project_name} have one or more failures",
            produced_artifact=None,
        )
    finally:
        docker_container.stop()
        docker_container.remove()

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
    bpm_file_path = config.depolyment_path.bpm_diagram_folder_path
    pr_number = config.pr_number
    try:
        deploy_diagram_to_modeler(
            logger, bpm_file_path, config.project_id, camunda_client, pr_number
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
