""" Step that deploys the docker image produced in the build stage to Kubernetes, using HELM. """
import re
from logging import Logger
from typing import Optional

from .k8s import deploy_helm_chart, CustomResourceDefinition
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

    @staticmethod
    def try_extract_endpoint(chart: dict[str, CustomResourceDefinition]) -> Optional[str]:
        ingress = chart.get('ingress-https-route')
        if ingress:
            routes = ingress.spec.get('routes', {})
            if routes:
                url = routes[0].get('match')
                return 'https://' + next(iter(re.findall(r'`(.*)`', url)))
        return None

    def execute(self, step_input: Input) -> Output:
        builder = ChartBuilder(step_input)
        chart = to_service_chart(builder)
        endpoint = self.try_extract_endpoint(chart)
        if endpoint:
            self._logger.info(f"Service {step_input.project.name} reachable at: {endpoint}")

        return deploy_helm_chart(self._logger, chart, step_input, builder.release_name)
