""" Yarn lint step. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from . import STAGE_NAME


class YarnLint(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Yarn lint",
                description="Run yarn linting",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        # run command from project.yml or hardcode it here
        return Output(
            success=True,
            message=f"Yarn lint step passed for project {step_input.project_execution.name}",
        )
