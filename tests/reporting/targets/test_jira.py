import json
from pathlib import Path

from atlassian import Jira

from src.mpyl.reporting.targets.jira import extract_ticket_from_branch, JiraTicket, to_markdown_summary, \
    to_github_markdown
from tests import root_test_path
from tests.test_resources.test_data import assert_roundtrip


class TestJiraReporter:
    test_resource_path = root_test_path / "reporting" / "test_resources"

    def test_should_print_results_as_string(self):
        ticket_json = json.loads(Path(self.test_resource_path / "jira_issue.json").read_text(encoding='utf-8'))
        ticket = JiraTicket.from_issue_response(ticket_json)
        assert ticket.ticket_id == 'TECH-290'
        assert ticket.issue_type == 'Story'
        assert ticket.summary == 'Update PR description in github with deployment info'
        assert ticket.description.startswith('Similarly to mpl *modules*, we _should_ update the PR details with card')

    def test_convert_jira_to_github_markdown(self):
        jira_markdown = Path(self.test_resource_path / "markdown_jira.md").read_text(encoding='utf-8')
        github_markdown = to_github_markdown(jira_markdown, 'http://vandebron.atlassian.com')
        assert_roundtrip(self.test_resource_path / "markdown_jira_github.md", github_markdown, overwrite=False)

    def test_ticket_to_summary(self):
        ticket_json = json.loads(Path(self.test_resource_path / "jira_issue.json").read_text(encoding='utf-8'))
        ticket = JiraTicket.from_issue_response(ticket_json)
        summary = to_markdown_summary(ticket)
        assert_roundtrip(self.test_resource_path / "markdown_jira_ticket_to_github.md", summary, overwrite=False)

    def test_should_extract_ticket_from_branch(self):
        assert extract_ticket_from_branch('feature/TICKET-281-slack-reporter') == 'TICKET-281'
        assert extract_ticket_from_branch('feature/TECH-281-slack-reporter') == 'TECH-281'
        assert extract_ticket_from_branch('feature/ARC-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore:arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/some-fix') is None
