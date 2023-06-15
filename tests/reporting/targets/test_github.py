from src.mpyl.reporting.targets.github import PullRequestReporter, GithubUpdateStategy
from tests.test_resources.test_data import get_config_values


class TestGithubReporter:
    reporter = PullRequestReporter(get_config_values(), update_stategy=GithubUpdateStategy.BODY)

    def test_replace_pr_body_empty(self):
        assert self.reporter._extract_pr_header(
            current_body=None
        ) == f"\n{self.reporter.body_separator}\n"

    def test_replace_pr_body(self):
        assert self.reporter._extract_pr_header(
            current_body="body"
        ) == f"body\n{self.reporter.body_separator}\n"

    def test_replace_pr_body_repeated(self):
        assert self.reporter._extract_pr_header(
            current_body=self.reporter._extract_pr_header(
                current_body="body"
            )
        ) == f"body\n{self.reporter.body_separator}\n"
