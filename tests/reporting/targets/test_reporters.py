from mpyl.reporting.targets import ReportAccumulator
from mpyl.reporting.targets.github import GithubOutcome
from mpyl.reporting.targets.slack import SlackOutcome


class TestReporters:
    def test_get_all_outcomes(self):
        outcomes = ReportAccumulator()
        outcomes.add(SlackOutcome(True))
        outcomes.add(SlackOutcome(False, Exception("test")))
        outcomes.add(GithubOutcome(False, Exception("github error")))
        assert outcomes.failures == [
            "SlackOutcome failed with exception test",
            "GithubOutcome failed with exception github error",
        ]
