""" Skip test step. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage


class BuildSkip(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Skip Build",
                description="Skip build step",
                version="0.0.1",
                stage=Stage.BUILD,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Skip build stage for project {step_input.project.name}")
        return Output(
            success=True,
            message=f"Skipped build stage for project {step_input.project.name}",
        )
