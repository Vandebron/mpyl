from src.mpyl.project import Stage
from src.mpyl.reporting.formatting.markdown import summary_to_markdown, run_result_to_markdown
from src.mpyl.utilities.junit import TestRunSummary
from tests import root_test_path
from tests.reporting import create_test_result, create_test_result_with_plan
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip


class TestMarkdownReporting:
    test_resource_path = root_test_path / "reporting" / "test_resources"

    def test_should_print_results_as_string(self):
        run_result = create_test_result()
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(self.test_resource_path / "markdown_run.md", simple_report)

    def test_should_print_results_with_plan_as_string(self):
        run_result = create_test_result_with_plan()
        simple_report = run_result_to_markdown(run_result)
        assert_roundtrip(self.test_resource_path / "markdown_run_with_plan.md", simple_report)

    def test_should_convert_test_summary_to_markdown(self):
        summary = TestRunSummary(tests=20, failures=2, errors=1, skipped=0)
        test_report = summary_to_markdown(summary)
        assert_roundtrip(self.test_resource_path / "test_run_summary.md", test_report)
