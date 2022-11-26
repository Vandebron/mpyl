from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output
from ...stage import Stage


class DeployEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Deploy',
            description='Dummy deploy step to test the framework',
            version='0.0.1',
            stage=Stage.DEPLOY
        ))

    def execute(self, input: Input) -> Output:
        self._logger.info(f"Deploying project {input.project.name}")
        return Output(success=True, message=f"Deployed project {input.project.name}")
