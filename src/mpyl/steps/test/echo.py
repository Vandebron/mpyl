""" Dummy test step to test the framework. """

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact
from ...project import Stage
from ...utilities.junit import TEST_OUTPUT_PATH_KEY


class TestEcho(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Echo Test',
            description='Dummy test step to test the framework',
            version='0.0.1',
            stage=Stage.TEST
        ), produced_artifact=ArtifactType.JUNIT_TESTS, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")
        artifact = input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                     spec={TEST_OUTPUT_PATH_KEY: 'target/tests'})
        return Output(success=True, message=f"Tested {step_input.project.name}", produced_artifact=artifact)
