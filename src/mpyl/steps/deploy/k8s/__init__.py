"""Kubernetes deployment related helper methods"""
from logging import Logger

from kubernetes import config, client

from .helm import ExternalHelmArguments
from ...deploy.k8s.resources import CustomResourceDefinition
from ....steps import Input, Output
from ....steps.deploy.k8s import helm
from ....steps.deploy.k8s.rancher import cluster_config, rancher_namespace_metadata


def upsert_namespace(logger: Logger, step_input: Input, context: str):
    properties = step_input.run_properties

    config.load_kube_config(context=context)
    logger.info(f"Deploying target {properties.target} and k8s context {context}")
    api = client.CoreV1Api()

    namespace = f'pr-{properties.versioning.pr_number}'
    meta_data = rancher_namespace_metadata(namespace, properties.target)

    namespaces = api.list_namespace(field_selector=f'metadata.name={namespace}')
    if len(namespaces.items) == 0 and not step_input.dry_run:
        api.create_namespace(
            client.V1Namespace(api_version='v1', kind='Namespace', metadata=meta_data))
    else:
        logger.info(f"Found namespace {namespace}")
    return namespace


def __upsert_namespace(logger, step_input):
    properties = step_input.run_properties
    context = cluster_config(properties.target).context
    namespace = upsert_namespace(logger, step_input, context)
    return context, namespace


def deploy_helm_chart(logger: Logger, chart: dict[str, CustomResourceDefinition], step_input: Input,
                      release_name: str) -> Output:
    context, namespace = __upsert_namespace(logger, step_input)
    return helm.install(logger, chart, step_input, release_name, namespace, context)


def deploy_external_helm_chart(logger: Logger, values: dict, step_input: Input,
                               chart_name: str, release_name: str, repo: str, version: str) -> Output:
    context, namespace = __upsert_namespace(logger, step_input)

    return helm.install_external(logger=logger, values=values, step_input=step_input, release_name=release_name,
                                 name_space=namespace, kube_context=context,
                                 helm_args=ExternalHelmArguments(chart_name=chart_name, repo=repo, version=version))
