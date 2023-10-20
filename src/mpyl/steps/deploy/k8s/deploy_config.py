from dataclasses import dataclass
from enum import Enum


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
