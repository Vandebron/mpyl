"""Configuration required for running bpmn"""
import os
from dataclasses import dataclass
from typing import Optional
from ...project import Target, TargetProperty


@dataclass(frozen=True)
class CamundaConfig:
    cluster_id: str
    client_id: str
    client_secret: str
    docker_directory_path: str
    docker_file_path: str
    bpm_project_path: str
    bpm_diagram_folder_path: str

    @staticmethod
    def from_config(config: dict, target: Target, root_path: str):
        camunda_config = config.get("camunda")
        if not camunda_config:
            raise KeyError("Camunda section needs to be defined in mpyl_config.yml")

        credentials = TargetProperty.from_config(
            camunda_config.get("zeebeCredentials")
        ).get_value(target)
        deploy_path = camunda_config.get("camundaDeploymentPath")
        return CamundaConfig(
            cluster_id=credentials.get("clusterId"),
            client_id=credentials.get("clientId"),
            client_secret=credentials.get("clientSecret"),
            docker_directory_path=deploy_path.get("dockerDirectoryPath"),
            docker_file_path=deploy_path.get("dockerFilePath"),
            bpm_project_path=deploy_path.get("bpmProjectPath"),
            bpm_diagram_folder_path=os.path.join(
                root_path, deploy_path.get("diagramResourcesPath")
            ),
        )
