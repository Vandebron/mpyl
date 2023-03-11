""" A dummy deploy step, which produces `mpyl.steps.models.ArtifactType.NONE`."""

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage


class DeployEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Deploy',
            description='Dummy deploy step to test the framework',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), ArtifactType.NONE, ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        artifact = step_input.required_artifact
        if not artifact:
            return Output(success=False, message=f"Step requires artifact of type {self.required_artifact}")

        self._logger.info(f"Deploying project {step_input.project.name} with artifact: {artifact.spec}")
        return Output(success=True, message=f"Deployed project {step_input.project.name}", produced_artifact=None)
