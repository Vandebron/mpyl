"""
Skip the postdeploy step.
Can be used to add the stage to the run plan, so you can run something else in your runner.
"""

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from . import STAGE_NAME


class PostdeploySkip(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Skip Postdeploy",
                description="Skip postdeploy step",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        self._logger.info(
            f"Skip postdeploy stage for project {step_input.project_execution.name}"
        )
        return Output(
            success=True,
            message=f"Skipped postdeploy stage for project {step_input.project_execution.name}",
        )
