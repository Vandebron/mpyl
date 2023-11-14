"""
Dagster-related utility methods
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class DagsterConfig:
    base_namespace: str
    workspace_config_map: str
    workspace_file_key: str
    daemon: str
    webserver: str
    global_service_account_override: Optional[str]

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
                global_service_account_override=dagster_config.get(
                    "globalServiceAccountOverride", None
                ),
            )
        except KeyError as exc:
            raise KeyError(f"Dagster config could not be loaded from {config}") from exc
