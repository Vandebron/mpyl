"""
This module contains the Dagster user-code-deployment values conversion
"""
from dataclasses import dataclass

from .....project import Project, get_env_variables
from .....steps.models import RunProperties
from .....utilities.docker import DockerConfig


@dataclass(frozen=True)
class Constants:
    HELM_CHART_REPO = "https://dagster-io.github.io/helm"
    CHART_NAME = "dagster/dagster-user-deployments"


def to_user_code_values(
    project: Project,
    name_suffix: str,
    run_properties: RunProperties,
    docker_config: DockerConfig,
) -> dict:
    return {
        "deployments": [
            {
                "dagsterApiGrpcArgs": ["--python-file", project.dagster.repo],
                "env": get_env_variables(project, run_properties.target),
                "envSecrets": [{"name": s.name} for s in project.dagster.secrets],
                "image": {
                    "pullPolicy": "Always",
                    "imagePullSecrets": [{"name": "bigdataregistry"}],
                    "tag": run_properties.versioning.identifier,
                    "repository": f"{docker_config.host_name}/{project.name}",
                },
                "includeConfigInLaunchedRuns": {"enabled": True},
                "name": f"{project.name}{name_suffix}",
                "port": 3030,
            },
        ],
        "nameOverride": "ucd",  # short for user-code-deployment
    }


def to_grpc_server_entry(host: str, location_name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": location_name, "port": port}}
