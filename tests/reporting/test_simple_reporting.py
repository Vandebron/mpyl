from src.mpyl.reporting.formatting.text import to_string, to_test_report
from src.mpyl.utilities.junit import JunitTestSpec
from tests import root_test_path
from tests.reporting import create_test_result
from tests.test_resources.test_data import assert_roundtrip


class TestReporting:
    test_resource_path = root_test_path / "reporting" / "formatting" / "test_resources"

    def test_should_print_results_as_string(self):
        run_result = create_test_result()
        simple_report = to_string(run_result)
        assert_roundtrip(self.test_resource_path / "simple_run.txt", simple_report)

    def test_should_convert_test_report_to_string(self):
        spec = JunitTestSpec(self.test_resource_path)
        test_report = to_test_report(spec)
        assert_roundtrip(
            self.test_resource_path / "simple_test.txt", test_report, overwrite=False
        )
