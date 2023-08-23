"""Kubernetes deployment related helper methods"""
from logging import Logger
from pathlib import Path
from typing import Optional

from kubernetes import config, client

from .helm import write_helm_chart
from ...deploy.k8s.resources import CustomResourceDefinition
from ...models import RunProperties
from ....project import Project, Target, ProjectName
from ....steps import Input, Output
from ....steps.deploy.k8s import helm
from ....steps.deploy.k8s.rancher import (
    cluster_config,
    rancher_namespace_metadata,
    ClusterConfig,
    render_templates,
)


def get_namespace(run_properties: RunProperties, project: Project) -> str:
    if run_properties.target == Target.PULL_REQUEST:
        return run_properties.versioning.identifier

    return get_namespace_from_project(project) or project.name


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


def deploy_helm_chart(
    logger: Logger,
    chart: dict[str, CustomResourceDefinition],
    step_input: Input,
    target: Target,
    release_name: str,
    delete_existing: bool = False,
) -> Output:
    run_properties = step_input.run_properties
    project = step_input.project
    dry_run = step_input.dry_run

    chart_path = write_helm_chart(
        logger, chart, Path(project.target_path), run_properties, release_name
    )

    if render_templates(run_properties):
        return helm.template(logger, chart_path, release_name)

    namespace = get_namespace(run_properties, project)
    rancher_config: ClusterConfig = cluster_config(target, run_properties)
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

    def get_namespace_for_linked_project(project_name: ProjectName):
        is_part_of_same_deploy_set = project_name in projects_to_deploy
        if is_part_of_same_deploy_set and pr_identifier:
            return f"pr-{pr_identifier}"
        return project_name.namespace

    def replace_namespace(env_value, project_name, namespace):
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
