""" Skip test step. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from . import STAGE_NAME


class TestSkip(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Skip Test",
                description="Skip test step",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Skip test stage for project {step_input.project.name}")
        return Output(
            success=True,
            message=f"Skipped test stage for project {step_input.project.name}",
        )
