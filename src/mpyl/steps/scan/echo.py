""" Dummy scan step to test the framework. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage


class ScanEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Scan',
            description='Dummy scan step to test the framework',
            version='0.0.1',
            stage=Stage.SCAN
        ), ArtifactType.NONE, ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Scanning project {step_input.project.name}")
        return Output(success=True, message=f"Scanned {step_input.project.name}", produced_artifact=None)
