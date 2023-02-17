import pytest

from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output, ArtifactType
from ...stage import Stage

class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Docker Test',
            description='Docker test step',
            version='0.0.1',
            stage=Stage.TEST
        ), ArtifactType.DOCKER_IMAGE, ArtifactType.DOCKER_IMAGE)



    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")
        return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=None)
