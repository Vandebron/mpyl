""" Step that deploys the docker image produced in the build stage to Kubernetes, using HELM. """

from logging import Logger

from .k8s import deploy_helm_chart
from .k8s.chart import ChartBuilder, to_service_chart
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
        builder = ChartBuilder(step_input)
        return deploy_helm_chart(self._logger, to_service_chart(builder), step_input, builder.release_name)
