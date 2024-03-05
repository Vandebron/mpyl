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

        config = TargetProperty.from_config(camunda_config).get_value(target)
        return CamundaConfig(
            cluster_id=str(config.get("clusterId")),
            client_id=str(config.get("clientId")),
            client_secret=str(config.get("clientSecret")),
            docker_directory_path=camunda_config.get("dockerDirectoryPath"),
            docker_file_path=camunda_config.get("dockerFilePath"),
            bpm_project_path=camunda_config.get("bpmProjectPath"),
            bpm_diagram_folder_path=os.path.join(
                root_path, camunda_config.get("diagramResourcesPath")
            ),
        )
