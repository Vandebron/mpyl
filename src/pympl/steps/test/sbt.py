from logging import Logger

from ..models import Meta, Input, Output, ArtifactType
from ..step import Step
from ...stage import Stage


class SbtTest(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Sbt Test',
            description='Dummy sbt test',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), ArtifactType.NONE, ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")

        return Output(success=True, message=f"Tested project {step_input.project.name}", produced_artifact=None)
