from src.mpyl.reporting.targets.slack import to_slack_markdown
from tests import root_test_path
from tests.test_resources.test_data import assert_roundtrip


class TestSlackReporter:
    test_resource_path = root_test_path / "reporting" / "test_resources"

    def test_convert_md_to_slack(self):
        with open(self.test_resource_path / "markdown_run.md", encoding='utf-8') as markdown:
            markdown_report = to_slack_markdown(markdown.read())
            assert_roundtrip(self.test_resource_path / "markdown_run_slack.md", markdown_report)
