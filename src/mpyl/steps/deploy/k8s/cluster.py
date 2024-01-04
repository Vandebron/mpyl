""" Utilities for creating rancher compatible helm charts. """

from dataclasses import dataclass
from typing import Optional, Any

from ...models import RunProperties
from ....project import Target, TargetProperty


@dataclass(frozen=True)
class ClusterConfig:
    name: str
    project_id: Optional[str]
    cluster_id: Optional[str]
    cluster_env: str
    context: str

    @staticmethod
    def from_config(config: dict):
        return ClusterConfig(
            name=config["name"],
            project_id=config.get("clusterId"),
            cluster_id=config.get("clusterId"),
            cluster_env=config["clusterEnv"],
            context=config["context"],
        )


def get_cluster_config(
    target: Target, run_properties: RunProperties, cluster_override: Optional[str]
) -> ClusterConfig:
    kubernetes_config = run_properties.config["kubernetes"]

    clusters = [
        ClusterConfig.from_config(cluster_config)
        for cluster_config in kubernetes_config["clusters"]
    ]

    default_cluster_name: str = TargetProperty.from_config(
        kubernetes_config["mainCluster"]
    ).get_value(target)

    default_cluster: ClusterConfig = next(
        cluster for cluster in clusters if cluster.name == default_cluster_name
    )

    if not default_cluster:
        raise ValueError(
            f"Default cluster {default_cluster_name} not found in list of clusters"
        )

    cluster_for_env = next(
        (cluster for cluster in clusters if cluster.name == cluster_override),
        default_cluster,
    )

    return cluster_for_env


def rancher_namespace_metadata(namespace: str, rancher_config: ClusterConfig):
    metadata: dict[str, Any] = {
        "name": namespace,
    }

    if rancher_config.project_id and rancher_config.cluster_id:
        metadata["annotations"] = {
            "field.cattle.io/projectId": f"{rancher_config.cluster_id}:{rancher_config.project_id}",
            "lifecycle.cattle.io/create.namespace-auth": "true",
        }
        metadata["labels"] = {
            "field.cattle.io/projectId": rancher_config.project_id,
            "kubernetes.io/metadata.name": namespace,
        }

    return metadata
