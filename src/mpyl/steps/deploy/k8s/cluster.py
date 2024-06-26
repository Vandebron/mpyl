""" Utilities for creating rancher compatible helm charts. """

from dataclasses import dataclass
from typing import Optional, Any

from ...models import RunProperties
from ....project import TargetProperty, Project


@dataclass(frozen=True)
class ClusterConfig:
    name: str
    cluster_id: Optional[str]
    cluster_env: str
    context: str

    @staticmethod
    def from_config(config: dict):
        return ClusterConfig(
            name=config["name"],
            cluster_id=config.get("clusterId"),
            cluster_env=config["clusterEnv"],
            context=config["context"],
        )


def get_cluster_config_for_project(
    run_properties: RunProperties, project: Project
) -> ClusterConfig:
    kubernetes_config = run_properties.config["kubernetes"]

    clusters = [
        ClusterConfig.from_config(cluster_config)
        for cluster_config in kubernetes_config["clusters"]
    ]

    default_cluster_name: str = TargetProperty.from_config(
        kubernetes_config["defaultCluster"]
    ).get_value(run_properties.target)

    cluster_override_name = (
        project.deployment.cluster.get_value(run_properties.target)
        if project.deployment and project.deployment.cluster
        else None
    )

    cluster_override = next(
        (cluster for cluster in clusters if cluster.name == cluster_override_name), None
    )

    if cluster_override_name and not cluster_override:
        raise ValueError(
            f"Cluster override {cluster_override_name} not found in list of clusters"
        )

    default_cluster: ClusterConfig = __get_default_cluster(
        clusters, default_cluster_name
    )

    if not default_cluster:
        raise ValueError(
            f"Default cluster {default_cluster_name} not found in list of clusters"
        )

    return cluster_override if cluster_override else default_cluster


def __get_default_cluster(clusters, default_cluster_name):
    return next(cluster for cluster in clusters if cluster.name == default_cluster_name)


def get_namespace_metadata(
    namespace: str, cluster_config: ClusterConfig, project_id: str
):
    metadata: dict[str, Any] = {
        "name": namespace,
    }

    if cluster_config.cluster_id:
        metadata["annotations"] = {
            "field.cattle.io/projectId": f"{cluster_config.cluster_id}:{project_id}",
            "lifecycle.cattle.io/create.namespace-auth": "true",
        }
        metadata["labels"] = {
            "field.cattle.io/projectId": project_id,
            "kubernetes.io/metadata.name": namespace,
        }

    return metadata
