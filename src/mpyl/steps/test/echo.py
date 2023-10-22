""" Dummy test step to test the framework. """

from logging import Logger
from pathlib import Path

from . import STAGE_NAME
from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact
from ...utilities.junit import JunitTestSpec

SAMPLE_JUNIT_RESULT = """
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="jest tests" tests="1" failures="0" errors="0" time="0.486">
  <testsuite name="undefined" errors="0" failures="0" skipped="0" timestamp="2023-03-29T02:51:00" time="0.244" tests="1">
    <testcase classname="Test Echo" name=" fake test case from TestEcho step" time="0.002">
    </testcase>
  </testsuite>
</testsuites>
""".strip()


class TestEcho(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Echo Test",
                description="Dummy test step to test the framework",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Testing project {step_input.project.name}")
        path = Path(step_input.project.target_path, "test_results")
        path.mkdir(parents=True, exist_ok=True)
        Path(path, "test.xml").write_text(SAMPLE_JUNIT_RESULT, encoding="utf-8")

        artifact = input_to_artifact(
            artifact_type=ArtifactType.JUNIT_TESTS,
            step_input=step_input,
            spec=JunitTestSpec(
                test_output_path=str(path),
                test_results_url=step_input.run_properties.details.tests_url,
            ),
        )
        return Output(
            success=True,
            message=f"Tested {step_input.project.name}",
            produced_artifact=artifact,
        )
