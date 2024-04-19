"""Configuration required for running bpm"""

import os
from dataclasses import dataclass
from ...project import Project, Target, TargetProperty


@dataclass(frozen=True)
class CamundaModelerAPI:
    base_url: str
    token_url: str

    @staticmethod
    def from_config(urls: dict):
        return CamundaModelerAPI(
            base_url=str(urls.get("baseUrl")),
            token_url=str(urls.get("tokenUrl")),
        )


@dataclass(frozen=True)
class CamundaModelerCredentials:
    client_id: str
    client_secret: str
    grant_type: str
    audience: str

    @staticmethod
    def from_config(credentials: dict):
        return CamundaModelerCredentials(
            client_id=str(credentials.get("clientId")),
            client_secret=str(credentials.get("clientSecret")),
            grant_type=str(credentials.get("grantType")),
            audience=str(credentials.get("audience")),
        )

    def to_dict(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": self.grant_type,
            "audience": self.audience,
        }


@dataclass(frozen=True)
class CamundaZeebeCredentials:
    cluster_id: str
    client_id: str
    client_secret: str

    @staticmethod
    def from_config(credentials: dict):
        return CamundaZeebeCredentials(
            cluster_id=str(credentials.get("clusterId")),
            client_id=str(credentials.get("clientId")),
            client_secret=str(credentials.get("clientSecret")),
        )


@dataclass(frozen=True)
class CamundaDeploymentPath:
    docker_directory_path: str
    docker_file_path: str
    bpm_project_path: str
    bpm_diagram_folder_path: str

    @staticmethod
    def from_config(deploy_path: dict, root_path: str):
        return CamundaDeploymentPath(
            docker_directory_path=str(deploy_path.get("dockerDirectoryPath")),
            docker_file_path=str(deploy_path.get("dockerFilePath")),
            bpm_project_path=str(deploy_path.get("bpmProjectPath")),
            bpm_diagram_folder_path=os.path.join(
                root_path, str(deploy_path.get("diagramResourcesPath"))
            ),
        )


@dataclass(frozen=True)
class CamundaConfig:
    modeler_api: CamundaModelerAPI
    modeler_credentials: CamundaModelerCredentials
    zeebe_credentials: CamundaZeebeCredentials
    depolyment_path: CamundaDeploymentPath
    project_id: str

    @staticmethod
    def from_config(config: dict, target: Target, project: Project):
        camunda_config = config.get("camunda")
        if not camunda_config:
            raise KeyError("Camunda section needs to be defined in mpyl_config.yml")

        modeler_urls = camunda_config.get("modelerAPI")
        modeler_credentials = camunda_config.get("modelerCredentials")
        zeebe_credentials = TargetProperty.from_config(
            camunda_config.get("zeebeCredentials")
        ).get_value(target)
        deploy_path = camunda_config.get("camundaDeploymentPath")
        return CamundaConfig(
            modeler_api=CamundaModelerAPI.from_config(modeler_urls),
            modeler_credentials=CamundaModelerCredentials.from_config(
                modeler_credentials
            ),
            zeebe_credentials=CamundaZeebeCredentials.from_config(zeebe_credentials),
            depolyment_path=CamundaDeploymentPath.from_config(
                deploy_path, project.root_path
            ),
            project_id=str(project.bpm.project_id),
        )
