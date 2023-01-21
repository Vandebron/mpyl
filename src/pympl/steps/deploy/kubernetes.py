from logging import Logger
from pathlib import Path

from kubernetes import config, client

from .k8s import helm
from .k8s.rancher import rancher_namespace_metadata
from .k8s.service import ServiceChart
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

        image_name = step_input.required_artifact.spec['image']

        dep = ServiceChart(step_input, image_name)

        templates = dep.to_chart()

        chart_path = Path(step_input.project.target_path) / "chart"

        config.load_kube_config()
        api = client.CoreV1Api()

        namespace = f'pr-{step_input.build_properties.versioning.pr_number}'
        meta_data = rancher_namespace_metadata(namespace, step_input.build_properties.target)

        namespaces = api.list_namespace(field_selector=f'metadata.name={namespace}')
        if len(namespaces.items) == 0:
            api.create_namespace(
                client.V1Namespace(api_version='v1', kind='Namespace', metadata=meta_data))
        else:
            self._logger.info(f"Found namespace {namespace}")

        helm_logs = helm.install(self._logger, step_input.project, namespace, chart_path, templates)
        self._logger.info(helm_logs)

        return Output(success=True, message=f"Deployed project {step_input.project.name}")
