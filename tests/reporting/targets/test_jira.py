import json
from pathlib import Path

from src.mpyl.reporting.targets.jira import extract_ticket_from_branch, JiraTicket
from tests import root_test_path


class TestJiraReporter:
    test_resource_path = root_test_path / "reporting" / "test_resources"

    def test_should_print_results_as_string(self):
        ticket_json = json.loads(Path(self.test_resource_path / "jira_issue.json").read_text(encoding='utf-8'))
        ticket = JiraTicket.from_issue_response(ticket_json)
        assert ticket.ticket_id == 'TECH-290'
        assert ticket.issue_type == 'Story'
        assert ticket.summary == 'Update PR description in github with deployment info'
        assert ticket.description.startswith('Similarly to mpl *modules*, we should update the PR details with card')

    def test_should_extract_ticket_from_branch(self):
        assert extract_ticket_from_branch('feature/TICKET-281-slack-reporter') == 'TICKET-281'
        assert extract_ticket_from_branch('feature/TECH-281-slack-reporter') == 'TECH-281'
        assert extract_ticket_from_branch('feature/ARC-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore:arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/some-fix') is None
