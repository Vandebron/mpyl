"""Configuration dataclasses for the deploy step."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ...models import RunProperties
from ....project import Project, Target


@dataclass(frozen=True)
class DeployAction(Enum):
    HELM_DEPLOY = "HelmDeploy"
    HELM_DRY_RUN = "HelmDryRun"
    HELM_TEMPLATE = "HelmTemplate"
    KUBERNETES_MANIFEST = "KubectlManifest"


@dataclass(frozen=True)
class DeployConfig:
    action: DeployAction
    output_path: str

    @staticmethod
    def from_config(values: dict):
        kube_config = values["kubernetes"]
        action: str = kube_config.get("deployAction", "HelmDeploy")
        output_path = kube_config.get("outputPath", "target/kubernetes")
        return DeployConfig(action=DeployAction(action), output_path=output_path)  # type: ignore


def get_namespace(run_properties: RunProperties, project: Project) -> str:
    if run_properties.target == Target.PULL_REQUEST:
        return run_properties.versioning.identifier

    return __get_namespace_from_project(project) or project.name


def __get_namespace_from_project(project: Project) -> Optional[str]:
    if project.deployment and project.deployment.namespace:
        return project.deployment.namespace

    return None
