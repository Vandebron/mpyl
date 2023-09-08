""" Utilities for creating rancher compatible helm charts. """

from dataclasses import dataclass

from ...models import RunProperties
from ....project import Target


@dataclass(frozen=True)
class ClusterConfig:
    project_id: str
    cluster_id: str
    cluster_env: str
    context: str

    @staticmethod
    def from_config(config: dict):
        return ClusterConfig(
            project_id=config["clusterId"],
            cluster_id=config["clusterId"],
            cluster_env=config["clusterEnv"],
            context=config["context"],
        )


def cluster_config(target: Target, run_properties: RunProperties) -> ClusterConfig:
    kubernetes_config = run_properties.config["kubernetes"]
    cluster_configs = kubernetes_config["rancher"]["cluster"]

    if target in {Target.PULL_REQUEST, Target.PULL_REQUEST_BASE}:
        return ClusterConfig.from_config(cluster_configs["test"])
    if target == Target.ACCEPTANCE:
        return ClusterConfig.from_config(cluster_configs["acceptance"])
    if target == Target.PRODUCTION:
        return ClusterConfig.from_config(cluster_configs["production"])
    raise ValueError(f"Unknown target {target}")


def rancher_namespace_metadata(namespace: str, rancher_config: ClusterConfig):
    return {
        "annotations": {
            "field.cattle.io/projectId": f"{rancher_config.cluster_id}:{rancher_config.project_id}",
            "lifecycle.cattle.io/create.namespace-auth": "true",
        },
        "labels": {
            "field.cattle.io/projectId": rancher_config.project_id,
            "kubernetes.io/metadata.name": namespace,
        },
        "name": namespace,
    }
