from logging import Logger

from .k8s.service import ServiceDeployment, to_yaml
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

        dep = ServiceDeployment(step_input)
        self._logger.info(to_yaml(dep))

        return Output(success=True, message=f"Deployed project {step_input.project.name}")
