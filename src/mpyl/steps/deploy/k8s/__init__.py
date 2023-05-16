"""Kubernetes deployment related helper methods"""
from logging import Logger

from kubernetes import config, client

from ...deploy.k8s.resources import CustomResourceDefinition
from ...models import RunProperties
from ....project import Project, Target
from ....steps import Input, Output
from ....steps.deploy.k8s import helm
from ....steps.deploy.k8s.rancher import cluster_config, rancher_namespace_metadata


def get_namespace(run_properties: RunProperties, project: Project) -> str:
    if run_properties.target == Target.PULL_REQUEST:
        return run_properties.versioning.identifier

    if project.deployment and project.deployment.namespace:
        return project.deployment.namespace

    return project.name


def upsert_namespace(logger: Logger, step_input: Input, context: str):
    properties = step_input.run_properties

    config.load_kube_config(context=context)
    logger.info(f"Deploying target {properties.target} and k8s context {context}")
    api = client.CoreV1Api()

    namespace = get_namespace(properties, step_input.project)
    meta_data = rancher_namespace_metadata(namespace, step_input)
    namespaces = api.list_namespace(field_selector=f'metadata.name={namespace}')

    if len(namespaces.items) == 0 and not step_input.dry_run:
        api.create_namespace(client.V1Namespace(api_version='v1', kind='Namespace', metadata=meta_data))
    else:
        logger.info(f"Found namespace {namespace}")

    return namespace


def deploy_helm_chart(logger: Logger, chart: dict[str, CustomResourceDefinition], step_input: Input,
                      release_name: str, delete_existing: bool = False) -> Output:
    context = cluster_config(step_input).context
    namespace = upsert_namespace(logger, step_input, context)

    return helm.install(logger, chart, step_input, release_name, namespace, context, delete_existing)
