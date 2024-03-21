"""Deploys the docker image produced in the build stage to Kubernetes, using HELM. """
import re
from logging import Logger
from typing import Optional

from . import STAGE_NAME
from .k8s import deploy_helm_chart, CustomResourceDefinition, DeployedHelmAppSpec
from .k8s.chart import ChartBuilder, to_service_chart
from .. import Step, Meta
from ..models import (
    Input,
    Output,
    ArtifactType,
    input_to_artifact,
)
from ...project import Target


class DeployKubernetes(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Kubernetes Deploy",
                description="Deploy to k8s",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    @staticmethod
    def match_to_url(match: str) -> str:
        return "https://" + next(iter(re.findall(r"`(.*)`", match.split(",")[-1])))

    @staticmethod
    def try_extract_hostname(
        chart: dict[str, CustomResourceDefinition], service_name: str
    ) -> Optional[str]:
        ingress = chart.get(f"{service_name}-ingress-0-https")
        if ingress:
            routes = ingress.spec.get("routes", {})
            if routes:
                match = routes[0].get("match")
                return DeployKubernetes.match_to_url(match)
        return None

    @staticmethod
    def get_endpoint(builder: ChartBuilder) -> str:
        step_input = builder.step_input
        has_specific_routes_configured = (
            builder.deployment.traefik is not None
            and step_input.run_properties.target == Target.PRODUCTION
        )
        hosts = (
            step_input.project_execution.project.deployment.traefik.hosts
            if step_input.project_execution.project.deployment
            and step_input.project_execution.project.deployment.traefik
            else []
        )
        has_swagger = hosts[0].has_swagger if hosts else True
        return (
            "/"
            if has_specific_routes_configured or not has_swagger
            else "/swagger/index.html"
        )

    def execute(self, step_input: Input) -> Output:
        builder = ChartBuilder(step_input)
        chart = to_service_chart(builder)

        deploy_result = deploy_helm_chart(
            self._logger, chart, step_input, builder.release_name
        )
        if deploy_result.success:
            hostname = self.try_extract_hostname(chart, builder.project.name)
            url = None
            if hostname:
                self._logger.info(
                    f"Service {step_input.project_execution.name} reachable at: {hostname}"
                )
                endpoint = self.get_endpoint(builder)
                url = f"{hostname}{endpoint}"
            artifact = input_to_artifact(
                ArtifactType.DEPLOYED_HELM_APP,
                step_input,
                spec=DeployedHelmAppSpec(url=f"{url}"),
            )
            return Output(
                success=True, message=deploy_result.message, produced_artifact=artifact
            )

        return deploy_result
