"""
This module contains the Dagster user-code-deployment values conversion
"""
from dataclasses import dataclass
from typing import Optional, List

from . import to_dict, CustomResourceDefinition
from ..chart import ChartBuilder, to_prometheus_chart
from .....project import get_env_variables
from .....steps.models import RunProperties
from .....utilities.docker import DockerConfig, registry_for_project
from .....utilities.helm import shorten_name


@dataclass(frozen=True)
class Constants:
    HELM_CHART_REPO = "https://dagster-io.github.io/helm"
    CHART_NAME = "dagster/dagster-user-deployments"


def to_grpc_server_entry(host: str, location_name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": location_name, "port": port}}


def collect_extra_manifests(
    builder: ChartBuilder, sealed_secrets_count: int, release_name: str
) -> List[CustomResourceDefinition]:
    sealed_secret_manifest = builder.to_sealed_secrets()
    sealed_secret_manifest.metadata.name = release_name

    extra_manifests_definitions = list(to_prometheus_chart(builder).values())

    if sealed_secrets_count > 0:
        extra_manifests_definitions.append(sealed_secret_manifest)

    return extra_manifests_definitions


def to_user_code_values(
    builder: ChartBuilder,
    release_name: str,
    name_suffix: str,
    run_properties: RunProperties,
    service_account_override: Optional[str],
    docker_config: DockerConfig,
) -> dict:
    project = builder.project
    docker_registry = registry_for_project(docker_config, project)

    global_override = {}
    create_local_service_account = service_account_override is None
    if not create_local_service_account:
        global_override = {"global": {"serviceAccountName": service_account_override}}

    sealed_secret_refs = []
    for sealed_secret_env in builder.get_sealed_secret_as_env_vars():
        sealed_secret_env.value_from.secret_key_ref.name = release_name
        sealed_secret_refs.append(to_dict(sealed_secret_env, skip_none=True))
    extra_manifests = collect_extra_manifests(
        builder, len(sealed_secret_refs), release_name
    )

    image_dict: dict = {
        "pullPolicy": "Always",
        "tag": run_properties.versioning.identifier,
        "repository": f"{docker_registry.host_name}/{project.name}",
    }
    if docker_registry.host_name == "azure":
        image_dict["imagePullSecrets"] = [{"name": "bigdataregistry"}]

    return (
        global_override
        | {
            "serviceAccount": {"create": create_local_service_account},
            # ucd, short for user-code-deployment
            "fullnameOverride": f"ucd-{shorten_name(project.name)}{name_suffix}",
            "deployments": [
                {
                    "dagsterApiGrpcArgs": [
                        "--python-file",
                        project.dagster.repo,
                    ],
                    "env": [
                        {"name": key, "value": value}
                        for key, value in get_env_variables(
                            project, run_properties.target
                        ).items()
                    ]
                    + sealed_secret_refs,
                    "envSecrets": [{"name": s.name} for s in project.dagster.secrets],
                    "image": image_dict,
                    "includeConfigInLaunchedRuns": {"enabled": True},
                    "name": release_name,
                    "port": 3030,
                    "resources": {
                        "requests": {"memory": "256Mi", "cpu": "50m"},
                        "limits": {"memory": "512Mi", "cpu": "1000m"},
                    },
                }
            ],
        }
        | (
            {"extraManifests": [to_dict(manifest) for manifest in extra_manifests]}
            if len(extra_manifests) > 0
            else {}
        )
    )
