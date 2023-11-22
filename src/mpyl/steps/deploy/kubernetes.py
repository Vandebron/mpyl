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
from ...stages.discovery import find_deploy_set
from ...utilities.repo import RepoConfig


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

    def execute(self, step_input: Input) -> Output:
        properties = step_input.run_properties
        builder = ChartBuilder(
            step_input,
            find_deploy_set(
                repo_config=RepoConfig.from_config(properties.config),
                tag=step_input.run_properties.versioning.tag,
            ),
        )
        chart = to_service_chart(builder)

        deploy_result = deploy_helm_chart(
            self._logger, chart, step_input, properties.target, builder.release_name
        )
        if deploy_result.success:
            hostname = self.try_extract_hostname(chart, builder.project.name)
            url = None
            if hostname:
                has_specific_routes_configured: bool = bool(
                    builder.deployment.traefik is not None
                    and properties.target == Target.PRODUCTION
                )
                self._logger.info(
                    f"Service {step_input.project.name} reachable at: {hostname}"
                )
                endpoint = (
                    "/" if has_specific_routes_configured else "/swagger/index.html"
                )
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
