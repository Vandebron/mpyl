from logging import Logger

from kubernetes import config, client

from .k8s import helm
from .k8s.rancher import rancher_namespace_metadata, cluster_config
from ..models import Meta, Input, Output, ArtifactType
from ..step import Step
from ...stage import Stage


class DeployKubernetes(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Deploy',
            description='Deploy to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Deploying project {step_input.project.name}")
        if not step_input.required_artifact:
            return Output(success=False, message=f"Step requires artifact of type {self.required_artifact}")

        properties = step_input.build_properties
        context = cluster_config(properties.target).context
        config.load_kube_config(context=context)
        self._logger.info(f"Deploying target {properties.target} and k8s context {context}")
        api = client.CoreV1Api()

        namespace = f'pr-{properties.versioning.pr_number}'
        meta_data = rancher_namespace_metadata(namespace, properties.target)

        namespaces = api.list_namespace(field_selector=f'metadata.name={namespace}')
        if len(namespaces.items) == 0:
            api.create_namespace(
                client.V1Namespace(api_version='v1', kind='Namespace', metadata=meta_data))
        else:
            self._logger.info(f"Found namespace {namespace}")

        helm_result = helm.install(self._logger, step_input, namespace, context)
        self._logger.info(helm_result.message)
        return helm_result
