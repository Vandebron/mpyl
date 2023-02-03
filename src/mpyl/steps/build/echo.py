"""This module defines a class named BuildEcho, which is a subclass of the Step class. It's used to perform a
dummy build step for testing purposes. The execute method logs a message indicating that
the project is being built and returns an Output object indicating the success of the build and a message. No actual
building is done in this class, as it is just meant to serve as a dummy build step."""

from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output, ArtifactType
from ...stage import Stage


class BuildEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Build',
            description='Dummy build step to test the framework',
            version='0.0.1',
            stage=Stage.BUILD
        ), ArtifactType.NONE, ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Building project {step_input.project.name}")
        return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=None)
