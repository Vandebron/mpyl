import os

import pytest

from src.mpyl.project import Target
from src.mpyl.reporting.targets.slack import to_slack_markdown, SlackReporter
from tests import root_test_path
from tests.reporting import create_test_result_with_plan, append_results
from tests.test_resources.test_data import assert_roundtrip


class TestSlackReporter:
    test_formatting_resource_path = (
        root_test_path / "reporting" / "formatting" / "test_resources"
    )
    test_targets_resource_path = (
        root_test_path / "reporting" / "targets" / "test_resources"
    )

    @pytest.mark.skip(reason="for a quick local test roundtrip")
    def test_send_test_message(self):
        run_result = create_test_result_with_plan()

        slack = SlackReporter(
            {
                "slack": {
                    "botToken": os.environ.get("SLACK_TOKEN"),
                    "icons": {
                        "success": "thug-parrot",
                        "failure": "sadparrot",
                        "building": "parrot",
                    },
                },
            },
            None,
            "MPyL test build",
            Target.PULL_REQUEST,
        )
        slack.send_report(run_result)
        append_results(run_result)
        slack.send_report(run_result)

    def test_convert_md_to_slack(self):
        with open(
            self.test_formatting_resource_path / "markdown_run_with_plan.md",
            encoding="utf-8",
        ) as markdown:
            markdown_report = to_slack_markdown(markdown.read())
            assert_roundtrip(
                self.test_targets_resource_path / "markdown_run_slack.md",
                markdown_report,
            )

    def test_should_lazy_match_links(self):
        md_with_links = (
            "*[nodeservice](https://nodeservice-96.test.nl/swagger/index.html)* "
            "*[sbtservice](https://sbtservice-96.test.nl/swagger/index.html)*"
        )

        assert (
            to_slack_markdown(md_with_links)
            == "*<https://nodeservice-96.test.nl/swagger/index.html|nodeservice>*"
            " *<https://sbtservice-96.test.nl/swagger/index.html|sbtservice>*"
        )
