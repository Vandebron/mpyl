"""Kubernetes deployment related helper methods"""
import re
from logging import Logger
from typing import Optional

from kubernetes import config, client

from ...deploy.k8s.resources import CustomResourceDefinition
from ...models import RunProperties
from ....project import Project, Target, ProjectName
from ....steps import Input, Output
from ....steps.deploy.k8s import helm
from ....steps.deploy.k8s.rancher import (
    cluster_config,
    rancher_namespace_metadata,
    ClusterConfig,
)


def get_namespace(run_properties: RunProperties, project: Project) -> Optional[str]:
    if run_properties.target == Target.PULL_REQUEST:
        return run_properties.versioning.identifier

    return get_namespace_from_project(project)


def get_namespace_from_project(project: Project) -> Optional[str]:
    if project.deployment and project.deployment.namespace:
        return project.deployment.namespace

    return None


def upsert_namespace(logger: Logger, step_input: Input, context: str):
    properties = step_input.run_properties

    config.load_kube_config(context=context)
    logger.info(f"Deploying target {properties.target} and k8s context {context}")
    api = client.CoreV1Api()

    namespace = get_namespace(properties, step_input.project)
    meta_data = rancher_namespace_metadata(
        namespace or step_input.project.name, step_input
    )
    namespaces = api.list_namespace(field_selector=f"metadata.name={namespace}")

    if len(namespaces.items) == 0 and not step_input.dry_run:
        api.create_namespace(
            client.V1Namespace(api_version="v1", kind="Namespace", metadata=meta_data)
        )
    else:
        logger.info(f"Found namespace {namespace}")

    return namespace


def deploy_helm_chart(
    logger: Logger,
    chart: dict[str, CustomResourceDefinition],
    step_input: Input,
    target_cluster: ClusterConfig,
    release_name: str,
    delete_existing: bool = False,
) -> Output:
    namespace = upsert_namespace(logger, step_input, target_cluster.context)

    return helm.install(
        logger,
        chart,
        step_input,
        release_name,
        namespace,
        target_cluster.context,
        delete_existing,
    )


def substitute_namespaces(
    env_vars: dict[str, str],
    all_projects: set[ProjectName],
    projects_to_deploy: set[ProjectName],
    pr_identifier: Optional[int],
) -> dict[str, str]:
    env = env_vars.copy()

    def has_fallback_namespace(env_value: str):
        regex = re.compile("{namespace=(.*?)}")
        return regex.search(env_value)

    def get_namespace_for_linked_project(env_value: str, project_name: ProjectName):
        is_part_of_same_deploy_set = project_name in projects_to_deploy
        if is_part_of_same_deploy_set and pr_identifier:
            return f"pr-{pr_identifier}"
        fallback_namespace = has_fallback_namespace(env_value)
        if fallback_namespace:
            return fallback_namespace.group(1)
        return project_name.namespace

    def replace_namespace(env_value: str, project_name: str):
        namespace = get_namespace_for_linked_project(env_value, project)
        search_value = project_name + r"\.{namespace}"
        if has_fallback_namespace(env_value):
            search_value = project_name + r"\.{namespace=.*?}"
        replace_value = project_name + "." + namespace
        return re.sub(search_value, replace_value, env_value)

    for project in all_projects:
        if project.namespace:
            for key, value in env.items():
                replaced_namespace = replace_namespace(value, project.name)
                updated_pr = (
                    replaced_namespace.replace("{PR-NUMBER}", str(pr_identifier))
                    if pr_identifier
                    else replaced_namespace
                )
                env[key] = updated_pr
    return env
