"""
Dagster-related utility methods
"""
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DagsterConfig:
    base_namespace: str
    workspace_config_map: str
    workspace_file_key: str
    daemon: str
    webserver: str

    @staticmethod
    def from_dict(config: Dict):
        try:
            dagster_config: Dict = config["dagster"]
            return DagsterConfig(
                base_namespace=dagster_config["baseNamespace"],
                workspace_config_map=dagster_config["workspaceConfigMap"],
                workspace_file_key=dagster_config["workspaceFileKey"],
                daemon=dagster_config["daemon"],
                webserver=dagster_config["webserver"],
            )
        except KeyError as exc:
            raise KeyError(f"Dagster config could not be loaded from {config}") from exc
