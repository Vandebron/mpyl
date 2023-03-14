""" Step that deploys the docker image produced in the build stage to Kubernetes, using HELM. """

from logging import Logger

from kubernetes import config, client

from .k8s import helm
from .k8s.chart import ChartBuilder, to_service_chart
from .k8s.rancher import rancher_namespace_metadata, cluster_config
from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage


class DeployKubernetes(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Deploy',
            description='Deploy to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Deploying project {step_input.project.name} with dry run: {step_input.dry_run}")
        if not step_input.required_artifact:
            return Output(success=False, message=f"Step requires artifact of type {self.required_artifact}")

        properties = step_input.run_properties
        context = cluster_config(properties.target).context

        config.load_kube_config(context=context)
        self._logger.info(f"Deploying target {properties.target} and k8s context {context}")
        api = client.CoreV1Api()

        namespace = f'pr-{properties.versioning.pr_number}'
        meta_data = rancher_namespace_metadata(namespace, properties.target)

        namespaces = api.list_namespace(field_selector=f'metadata.name={namespace}')
        if len(namespaces.items) == 0 and not step_input.dry_run:
            api.create_namespace(
                client.V1Namespace(api_version='v1', kind='Namespace', metadata=meta_data))
        else:
            self._logger.info(f"Found namespace {namespace}")

        builder = ChartBuilder(step_input)
        return helm.install(self._logger, to_service_chart(builder), step_input, builder.release_name, namespace,
                            context)
