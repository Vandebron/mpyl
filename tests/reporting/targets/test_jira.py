from src.mpyl.reporting.targets.jira import extract_ticket_from_branch


class TestJiraReporter:

    def test_should_extract_ticket_from_branch(self):
        assert extract_ticket_from_branch('feature/TICKET-281-slack-reporter') == 'TICKET-281'
        assert extract_ticket_from_branch('feature/TECH-281-slack-reporter') == 'TECH-281'
        assert extract_ticket_from_branch('feature/ARC-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore/arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('chore:arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('arc-590-slack-reporter') == 'ARC-590'
        assert extract_ticket_from_branch('feature/some-fix') is None
