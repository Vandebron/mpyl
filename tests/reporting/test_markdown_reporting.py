from datetime import datetime

from src.mpyl.reporting.formatting.markdown import (
    summary_to_markdown,
    run_result_to_markdown,
)
from src.mpyl.steps.models import Output, Artifact, ArtifactType
from src.mpyl.steps.executor import StepResult, ExecutionException
from src.mpyl.utilities.junit import (
    TestRunSummary,
    JunitTestSpec,
)
from tests import root_test_path
from tests.reporting import (
    create_test_result,
    create_test_result_with_plan,
    append_results,
)
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip, TestStage


class TestMarkdownReporting:
    test_resource_path = root_test_path / "reporting" / "formatting" / "test_resources"

    def test_should_print_results_as_string(self):
        run_result = create_test_result()
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(self.test_resource_path / "markdown_run.md", simple_report)

    def test_should_print_exception(self):
        run_result = create_test_result()
        run_result.exception = ExecutionException(
            "sbtProject", "Build SBT", "Build", "Something went wrong"
        )
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(
            self.test_resource_path / "markdown_run_with_exception.md", simple_report
        )

    def test_should_print_results_with_plan_as_string(self):
        run_result = create_test_result_with_plan()
        append_results(run_result)
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(
            self.test_resource_path / "markdown_run_with_plan.md", simple_report
        )

    def test_should_convert_test_summary_to_markdown(self):
        summary = TestRunSummary(tests=20, failures=2, errors=1, skipped=0)
        test_report = summary_to_markdown(summary)
        assert_roundtrip(self.test_resource_path / "test_run_summary.md", test_report)

    def test_should_measure_progress(self):
        result = create_test_result_with_plan()
        assert result.progress_fraction == 0.0, "Should start at zero progress"
        result.append(
            StepResult(
                stage=TestStage.build(),
                project=test_data.get_project(),
                output=Output(success=False, message="Build failed"),
                timestamp=datetime.fromisoformat("2019-01-04T16:41:24+02:00"),
            )
        )
        assert round(result.progress_fraction * 100) == 25, "Should be at one quarter"
        append_results(result)
        assert result.progress_fraction == 1.0, "Should be 100% at end of run"

    def test_should_combine_duplicate_urls(self):
        run_result = create_test_result()
        run_result.append(
            StepResult(
                stage=TestStage.test(),
                project=test_data.get_project(),
                output=Output(
                    success=True,
                    message="Tests successful",
                    produced_artifact=Artifact(
                        artifact_type=ArtifactType.JUNIT_TESTS,
                        revision="revision",
                        producing_step="Jest",
                        spec=JunitTestSpec(
                            test_output_path=str(self.test_resource_path),
                            test_results_url="http://localhost/tests",
                            test_results_summary=TestRunSummary(
                                tests=99, failures=1, errors=0, skipped=0
                            ),
                        ),
                    ),
                ),
                timestamp=datetime.fromisoformat("2019-01-04T16:41:24+02:00"),
            )
        )
        run_result.append(
            StepResult(
                stage=TestStage.test(),
                project=test_data.get_project(),
                output=Output(
                    success=True,
                    message="Tests successful",
                    produced_artifact=Artifact(
                        artifact_type=ArtifactType.JUNIT_TESTS,
                        revision="revision",
                        producing_step="Cypress",
                        spec=JunitTestSpec(
                            test_output_path=str(self.test_resource_path),
                            test_results_url="https://cypress.io",
                            test_results_summary=TestRunSummary(
                                tests=3, failures=1, errors=0, skipped=0
                            ),
                        ),
                    ),
                ),
                timestamp=datetime.fromisoformat("2019-01-04T16:41:24+02:00"),
            )
        )
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(
            self.test_resource_path / "markdown_run_multiple_urls.md", simple_report
        )
