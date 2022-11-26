from logging import Logger

from ..step import Step

from ..models import Meta, Input, Output
from ...stage import Stage


class BuildEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Build',
            description='Dummy build step to test the framework',
            version='0.0.1',
            stage=Stage.BUILD
        ))

    def execute(self, ipt: Input) -> Output:
        self._logger.info(f"Building project {ipt.project.name}")
        return Output(success=True, message=f"Built {ipt.project.name}")
