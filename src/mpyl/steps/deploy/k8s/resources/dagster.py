"""
This module contains the Dagster user-code-deployment values conversion
"""
from dataclasses import dataclass
from typing import Optional

from .....project import Project, get_env_variables
from .....steps.models import RunProperties
from .....utilities.docker import DockerConfig, registry_for_project
from .....utilities.helm import shorten_name


@dataclass(frozen=True)
class Constants:
    HELM_CHART_REPO = "https://dagster-io.github.io/helm"
    CHART_NAME = "dagster/dagster-user-deployments"


def to_user_code_values(
    project: Project,
    name_suffix: str,
    run_properties: RunProperties,
    service_account_override: Optional[str],
    docker_config: DockerConfig,
) -> dict:
    docker_registry = registry_for_project(docker_config, project)

    global_override = {}
    create_local_service_account = service_account_override is None
    if not create_local_service_account:
        global_override = {"global": {"serviceAccountName": service_account_override}}

    return global_override | {
        "serviceAccount": {"create": create_local_service_account},
        "fullnameOverride": f"ucd-{shorten_name(project.name)}{name_suffix}",  # short for user-code-deployment
        "deployments": [
            {
                "dagsterApiGrpcArgs": ["--python-file", project.dagster.repo],
                "env": get_env_variables(project, run_properties.target),
                "envSecrets": [{"name": s.name} for s in project.dagster.secrets],
                "image": {
                    "pullPolicy": "Always",
                    "imagePullSecrets": [{"name": "bigdataregistry"}],
                    "tag": run_properties.versioning.identifier,
                    "repository": f"{docker_registry.host_name}/{project.name}",
                },
                "includeConfigInLaunchedRuns": {"enabled": True},
                "name": f"{project.name}{name_suffix}",
                "port": 3030,
            },
        ],
    }


def to_grpc_server_entry(host: str, location_name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": location_name, "port": port}}
