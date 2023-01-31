from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output, ArtifactType
from ...stage import Stage


class DeployEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Deploy',
            description='Dummy deploy step to test the framework',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), ArtifactType.NONE, ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Deploying project {step_input.project.name}")
        artifact = step_input.required_artifact
        if artifact:
            self._logger.info(f"Deploying {artifact.artifact_type} {artifact.spec['image']}")
        else:
            return Output(success=False, message="Required artifact not found", produced_artifact=None)
        return Output(success=True, message=f"Deployed project {step_input.project.name}", produced_artifact=None)
