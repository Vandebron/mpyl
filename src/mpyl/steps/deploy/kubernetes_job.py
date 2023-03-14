""" A step to deploy a job to kubernetes. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage


class DeployKubernetesJob(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Job Deploy',
            description='Deploy a job to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        return Output(success=True, message='Dummy Implementation')
