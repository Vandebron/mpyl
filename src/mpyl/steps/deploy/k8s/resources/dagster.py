"""
This module contains the Dagster user-code-deployment values conversion
"""
from dataclasses import dataclass
from typing import Optional, List

from kubernetes.client import V1EnvVar

from . import to_dict
from .sealed_secret import V1SealedSecret
from .. import CustomResourceDefinition
from ..chart import ChartBuilder
from .....project import Project, get_env_variables
from .....steps.models import RunProperties
from .....utilities.docker import DockerConfig, registry_for_project
from .....utilities.helm import shorten_name


@dataclass(frozen=True)
class Constants:
    HELM_CHART_REPO = "https://dagster-io.github.io/helm"
    CHART_NAME = "dagster/dagster-user-deployments"


def to_grpc_server_entry(host: str, location_name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": location_name, "port": port}}


def to_user_code_values(
    builder: ChartBuilder,
    release_name: str,
    name_suffix: str,
    run_properties: RunProperties,
    service_account_override: Optional[str],
    docker_config: DockerConfig
) -> dict:
    docker_registry = registry_for_project(docker_config, builder.project)

    global_override = {}
    create_local_service_account = service_account_override is None
    if not create_local_service_account:
        global_override = {"global": {"serviceAccountName": service_account_override}}

    sealed_secret_refs = []
    for sealed_secret_env in builder.get_sealed_secret_as_env_vars():
        sealed_secret_env.value_from.secret_key_ref.name = release_name
        sealed_secret_refs.append(to_dict(sealed_secret_env, skip_none=True))

    extra_manifests = {}
    sealed_secret_manifest = builder.to_sealed_secrets()
    sealed_secret_manifest.metadata.name = release_name
    if sealed_secret_manifest.secrets:
        extra_manifests = {"extraManifests": [to_dict(sealed_secret_manifest, skip_none=True)]}

    return global_override | extra_manifests | {
        "serviceAccount": {"create": create_local_service_account},
        "fullnameOverride": f"ucd-{shorten_name(builder.project.name)}{name_suffix}",  # short for user-code-deployment
        "deployments": [
            {
                "dagsterApiGrpcArgs": ["--python-file", builder.project.dagster.repo],
                "env": [
                    {"name": key, "value": value}
                    for key, value in get_env_variables(
                        builder.project, run_properties.target
                    ).items()
                ]
                + sealed_secret_refs,
                "envSecrets": [{"name": s.name} for s in builder.project.dagster.secrets],
                "image": {
                    "pullPolicy": "Always",
                    "imagePullSecrets": [{"name": "bigdataregistry"}],
                    "tag": run_properties.versioning.identifier,
                    "repository": f"{docker_registry.host_name}/{builder.project.name}",
                },
                "includeConfigInLaunchedRuns": {"enabled": True},
                "name": release_name,
                "port": 3030,
                "resources": {
                    "requests": {"memory": "256Mi", "cpu": "50m"},
                    "limits": {"memory": "512Mi", "cpu": "1000m"},
                }
            }
        ]
    }
