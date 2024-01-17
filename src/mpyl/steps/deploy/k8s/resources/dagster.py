"""
This module contains the Dagster user-code-deployment values conversion
"""
from dataclasses import dataclass
from typing import Optional, List

from . import to_dict
from .. import CustomResourceDefinition
from .....project import Project, get_env_variables, Deployment
from .....steps.models import RunProperties
from .....utilities.docker import DockerConfig, registry_for_project
from .....utilities.helm import shorten_name


@dataclass(frozen=True)
class Constants:
    HELM_CHART_REPO = "https://dagster-io.github.io/helm"
    CHART_NAME = "dagster/dagster-user-deployments"


# where to place this, and maybe split it into two functions, secretKeyRef() and valueFrom()
def to_env_secret_key_ref(secret_key: str, name: str) -> dict:
    return {
        "name": secret_key,
        "valueFrom": {
            "secretKeyRef": {
                "name": name,
                "key": secret_key,
                "optional": False,
            }
        },
    }


def sealed_secrets_to_dict(
    release_name: str, deployment: Optional[Deployment]
) -> List[dict]:
    if deployment:
        return [
            to_env_secret_key_ref(sealed_secret.key, release_name)
            for sealed_secret in deployment.properties.sealed_secret
        ]
    return []


def to_user_code_values(
    project: Project,
    release_name: str,
    name_suffix: str,
    run_properties: RunProperties,
    service_account_override: Optional[str],
    docker_config: DockerConfig,
    extra_manifests: Optional[List[CustomResourceDefinition]] = None,
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
                "env": [
                    {"name": key, "value": value}
                    for key, value in get_env_variables(
                        project, run_properties.target
                    ).items()
                ]
                + sealed_secrets_to_dict(release_name, project.deployment),
                "envSecrets": [{"name": s.name} for s in project.dagster.secrets],
                "image": {
                    "pullPolicy": "Always",
                    "imagePullSecrets": [{"name": "bigdataregistry"}],
                    "tag": run_properties.versioning.identifier,
                    "repository": f"{docker_registry.host_name}/{project.name}",
                },
                "includeConfigInLaunchedRuns": {"enabled": True},
                "name": release_name,
                "port": 3030,
                "resources": {
                    "requests": {"memory": "256Mi", "cpu": "50m"},
                    "limits": {"memory": "512Mi", "cpu": "1000m"},
                },
            },
        ],
        "extraManifests": [to_dict(manifest) for manifest in extra_manifests]
        if extra_manifests
        else [],
    }


def to_grpc_server_entry(host: str, location_name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": location_name, "port": port}}
