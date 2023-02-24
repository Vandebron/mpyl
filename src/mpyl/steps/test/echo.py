""" Dummy test step to test the framework. """

from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output, ArtifactType
from ...project import Stage


class TestEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Test',
            description='Dummy test step to test the framework',
            version='0.0.1',
            stage=Stage.TEST
        ), ArtifactType.NONE, ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")
        return Output(success=True, message=f"Tested {step_input.project.name}", produced_artifact=None)
