"""Kubernetes deployment related helper methods"""
import datetime
import os
from dataclasses import dataclass
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import Optional

from kubernetes import config, client
from kubernetes.client import V1ConfigMap, ApiException, V1Deployment
from ruamel.yaml import yaml_object, YAML
import yaml as dict_to_yaml_str

from .helm import write_helm_chart, GENERATED_WARNING
from ...deploy.k8s.resources import CustomResourceDefinition
from ...models import RunProperties, input_to_artifact, ArtifactType, ArtifactSpec
from ....project import Project, Target, ProjectName
from ....steps import Input, Output
from ....steps.deploy.k8s import helm
from ....steps.deploy.k8s.rancher import (
    cluster_config,
    rancher_namespace_metadata,
    ClusterConfig,
)
from ....steps.deploy.k8s.resources import to_yaml

yaml = YAML()


@yaml_object(yaml)
@dataclass
class DeployedHelmAppSpec(ArtifactSpec):
    yaml_tag = "!DeployedHelmAppSpec"
    url: Optional[str]


@yaml_object(yaml)
@dataclass
class RenderedHelmChartSpec(ArtifactSpec):
    yaml_tag = "!RenderedHelmChartSpec"
    chart_path: str


@yaml_object(yaml)
@dataclass
class KubernetesManifestSpec(ArtifactSpec):
    yaml_tag = "!KubernetesManifestSpec"
    manifest_file_path: str


@dataclass(frozen=True)
class DeployAction(Enum):
    HELM_DEPLOY = "HelmDeploy"
    HELM_DRY_RUN = "HelmDryRun"
    HELM_TEMPLATE = "HelmTemplate"
    KUBERNETES_MANIFEST = "KubectlManifest"


@dataclass(frozen=True)
class DeployConfig:
    action: DeployAction
    output_path: str

    @staticmethod
    def from_config(values: dict):
        kube_config = values["kubernetes"]
        action: str = kube_config.get("deployAction", "HelmDeploy")
        output_path = kube_config.get("outputPath", "target/kubernetes")
        return DeployConfig(action=DeployAction(action), output_path=output_path)  # type: ignore


def get_namespace(run_properties: RunProperties, project: Project) -> str:
    if run_properties.target == Target.PULL_REQUEST:
        return run_properties.versioning.identifier

    return get_namespace_from_project(project) or project.name


def rollout_restart_deployment(
    logger: Logger, apps_api: client.AppsV1Api, namespace: str, deployment: str
) -> Output:
    # from https://stackoverflow.com/a/67491253
    now = datetime.datetime.utcnow()
    now_str = now.isoformat("T") + "Z"
    body = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {"kubectl.kubernetes.io/restartedAt": now_str}
                }
            }
        }
    }
    try:
        logger.info(f"Starting rollout restart of {deployment}...")
        _, status_code, _ = apps_api.patch_namespaced_deployment_with_http_info(
            deployment, namespace, body, pretty="true"
        )
        return Output(
            success=True,
            message=f"Rollout restart of {deployment} finished with statuscode {status_code}",
        )
    except ApiException as api_exception:
        return Output(
            success=False,
            message=f"Exception when calling AppsV1Api -> patch_namespaced_deployment: {api_exception}\n"
            f"{deployment} was NOT restarted",
        )


def get_namespace_from_project(project: Project) -> Optional[str]:
    if project.deployment and project.deployment.namespace:
        return project.deployment.namespace

    return None


def upsert_namespace(
    logger: Logger,
    namespace: str,
    dry_run: bool,
    run_properties: RunProperties,
    rancher_config: ClusterConfig,
) -> None:
    config.load_kube_config(context=rancher_config.context)
    logger.info(
        f"Deploying target {run_properties.target} and k8s context {rancher_config.context}"
    )
    api = client.CoreV1Api()

    meta_data = rancher_namespace_metadata(namespace, rancher_config)
    namespaces = api.list_namespace(field_selector=f"metadata.name={namespace}")

    if len(namespaces.items) == 0 and not dry_run:
        api.create_namespace(
            client.V1Namespace(api_version="v1", kind="Namespace", metadata=meta_data)
        )
    else:
        logger.info(f"Found namespace {namespace}")


def render_manifests(chart: dict[str, CustomResourceDefinition]):
    result = f"{GENERATED_WARNING}\n"
    for name, template_content in sorted(chart.items()):
        manifest = render_crd(name, template_content)
        result += manifest
    return result


def render_crd(name: str, crd: CustomResourceDefinition):
    return f"---\n# {name}\n{to_yaml(crd)}"


def write_manifest(
    release_name: str, target_path: Path, chart: dict[str, CustomResourceDefinition]
) -> Path:
    if not target_path.exists():
        os.makedirs(target_path, exist_ok=True)
    manifests = render_manifests(chart)
    manifest_file = target_path / f"{release_name}-manifest.yml"
    manifest_file.write_text(manifests, "utf-8")
    return manifest_file


def get_config_map(
    core_api: client.CoreV1Api, namespace: str, config_map_name: str
) -> V1ConfigMap:
    user_code_config_map: V1ConfigMap = core_api.read_namespaced_config_map(
        config_map_name, namespace
    )
    return user_code_config_map


def get_version_of_deployment(
    apps_api: client.AppsV1Api, namespace: str, deployment: str, version_label: str
) -> str:
    v1deployment: V1Deployment = apps_api.read_namespaced_deployment(
        deployment, namespace
    )
    return v1deployment.metadata.labels[version_label]


def update_config_map_field(
    config_map: V1ConfigMap, field: str, data: dict
) -> V1ConfigMap:
    config_map.data[field] = dict_to_yaml_str.dump(data)
    return config_map


def replace_config_map(
    core_api: client.CoreV1Api,
    namespace: str,
    config_map_name: str,
    config_map: V1ConfigMap,
) -> Output:
    try:
        _, status_code, _ = core_api.replace_namespaced_config_map_with_http_info(
            config_map_name, namespace, config_map
        )
        return Output(
            success=True,
            message=f"ConfigMap Update of {config_map_name} finished with statuscode {status_code}",
        )
    except ApiException as api_exception:
        return Output(
            success=False,
            message=f"Exception when calling CoreV1Api -> replace_namespaced_config_map: {api_exception}\n",
        )


def deploy_helm_chart(  # pylint: disable=too-many-locals
    logger: Logger,
    chart: dict[str, CustomResourceDefinition],
    step_input: Input,
    target: Target,
    release_name: str,
    delete_existing: bool = False,
) -> Output:
    run_properties = step_input.run_properties
    project = step_input.project

    deploy_config = DeployConfig.from_config(run_properties.config)

    action = deploy_config.action.value
    if action == DeployAction.KUBERNETES_MANIFEST.value:  # pylint: disable=no-member
        path = Path(project.root_path, deploy_config.output_path)
        file_path = write_manifest(release_name, path, chart)

        artifact = input_to_artifact(
            ArtifactType.KUBERNETES_MANIFEST,
            step_input,
            spec=KubernetesManifestSpec(str(file_path)),
        )

        return Output(
            success=True,
            message=f"Wrote kubectl manifest to {path}",
            produced_artifact=artifact,
        )

    chart_path = write_helm_chart(
        logger, chart, Path(project.target_path), run_properties, release_name
    )

    if action == DeployAction.HELM_TEMPLATE.value:  # pylint: disable=no-member
        template_path = helm.template(logger, chart_path, release_name)
        artifact = input_to_artifact(
            ArtifactType.KUBERNETES_MANIFEST,
            step_input,
            spec=RenderedHelmChartSpec(str(template_path)),
        )
        return Output(
            success=True,
            message=f"Chart templated to {template_path}",
            produced_artifact=artifact,
        )

    namespace = get_namespace(run_properties, project)
    rancher_config: ClusterConfig = cluster_config(target, run_properties)
    dry_run = (
        step_input.dry_run
        or action == DeployAction.HELM_DRY_RUN.value  # pylint: disable=no-member
    )
    upsert_namespace(
        logger,
        namespace,
        dry_run,
        run_properties,
        rancher_config,
    )

    upsert_namespace(logger, namespace, dry_run, run_properties, rancher_config)
    return helm.install(
        logger,
        chart_path,
        dry_run,
        release_name,
        namespace,
        rancher_config.context,
        delete_existing,
    )


def substitute_namespaces(
    env_vars: dict[str, str],
    all_projects: set[ProjectName],
    projects_to_deploy: set[ProjectName],
    pr_identifier: Optional[int],
) -> dict[str, str]:
    """
    Substitute namespaces in environment variables.

    In the project yamls we define references to other projects with e.g.:

    ```yaml
    - key: SOME_SERVICE_URL:
      all: http://serviceName.{namespace}.svc.cluster.local
    ```

    When the env var is substituted, first the referenced service (serviceName) is looked up in the list of projects.
    If it is part of the deploy set, and we're in deploying to target PullRequest,
    the namespace is subsituted with the PR namespace (pr-XXXX).
    Else is substituted with the namespace of the referenced project.

    Note that the name of the service in the env var is case-sensitive!

    :param env_vars: environment variables to substitute
    :param all_projects: all project in repo
    :param projects_to_deploy: projects in deploy set
    :param pr_identifier: PR number if applicable
    :return: dictionary of substituted env vars
    """
    env = env_vars.copy()

    def get_namespace_for_linked_project(project_name: ProjectName) -> str:
        is_part_of_same_deploy_set = project_name in projects_to_deploy
        if is_part_of_same_deploy_set and pr_identifier:
            return f"pr-{pr_identifier}"
        return project_name.namespace or project.name

    def replace_namespace(env_value: str, project_name: str, namespace: str) -> str:
        search_value = project_name + ".{namespace}"
        replace_value = project_name + "." + namespace
        return env_value.replace(search_value, replace_value)

    for project in all_projects:
        if project.namespace:
            linked_project_namespace = get_namespace_for_linked_project(project)
            for key, value in env.items():
                replaced_namespace = replace_namespace(
                    value, project.name, linked_project_namespace
                )
                updated_pr = (
                    replaced_namespace.replace("{PR-NUMBER}", str(pr_identifier))
                    if pr_identifier
                    else replaced_namespace
                )
                env[key] = updated_pr
    return env
