import argparse
import logging
import sys
from logging import Logger

logging.basicConfig(level=logging.INFO)


def main(log: Logger, args: argparse.Namespace):
    if args.local:
        from src.mpyl.reporting.targets.jira import JiraReporter
        from src.mpyl.steps.models import RunProperties
        from src.mpyl.utilities.pyaml_env import parse_config
        from src.mpyl.cli.commands.build.mpyl import run_mpyl, MpylRunParameters, MpylRunConfig, MpylCliParameters

    else:
        from mpyl.reporting.targets.jira import JiraReporter
        from mpyl.steps.models import RunProperties
        from mpyl.utilities.pyaml_env import parse_config
        from mpyl.cli.commands.build.mpyl import run_mpyl, MpylRunParameters, MpylRunConfig, MpylCliParameters

    config = parse_config("mpyl_config.yml")
    properties = parse_config("run_properties.yml")
    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    params = MpylRunParameters(
        run_config=MpylRunConfig(config=config, run_properties=run_properties),
        parameters=MpylCliParameters(
            local=args.local,
            verbose=args.verbose,
            all=args.all
        )
    )
    check = None
    slack_channel = None
    slack_personal = None
    jira = None
    github_comment = None

    if not args.local:
        from mpyl.reporting.targets.github import CommitCheck
        from mpyl.reporting.targets.slack import SlackReporter
        from mpyl.steps.run import RunResult
        from mpyl.reporting.targets.github import PullRequestComment
        from mpyl.reporting.targets.jira import JiraTicket, JiraConfig, extract_ticket_from_branch, \
            create_jira_for_config, to_github_markdown

        jira_config = JiraConfig.from_config(config=config)
        jira = create_jira_for_config(jira_config)
        ticket = extract_ticket_from_branch(run_properties.versioning.branch)
        issue = jira.get_issue(ticket)
        jira_ticket = JiraTicket.from_issue_response(issue)
        log.info(jira_ticket.summary)
        log.info(jira_ticket.description)
        ticket_markdown = to_github_markdown(jira_ticket.description, jira_config.site)
        check = CommitCheck(config=config, logger=log)

        def compose_pr_comment() -> str:
            return ticket_markdown

        github_comment = PullRequestComment(config=config, compose_function=compose_pr_comment)
        slack_channel = SlackReporter(
            config,
            '#project-mpyl-notifications',
            f'MPyL test {run_properties.versioning.identifier}'
        )

        if run_properties.details.user_email:
            slack_personal = SlackReporter(config, None, f'MPyL test {run_properties.versioning.identifier}')

        jira = JiraReporter(config=config, branch=run_properties.versioning.branch, logger=log)
        check.send_report(RunResult(run_properties=run_properties, run_plan={}))

    run_result = run_mpyl(params, slack_personal)

    if not args.local:
        check.send_report(run_result)
        slack_channel.send_report(run_result)
        jira.send_report(run_result)
        github_comment.send_report(run_result)

    sys.exit(0 if run_result.is_success else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple MPL pipeline')
    parser.add_argument('--local', '-l', help='a local developer run', default=False, action='store_true')
    parser.add_argument('--all', '-a', help='build and test everything, regardless of the changes that were made',
                        default=False, action='store_true')
    parser.add_argument('--dryrun', '-d', help="don't push or deploy images", default=False, action='store_true')
    parser.add_argument('--verbose', '-v', help="switch to DEBUG level logging", default=False, action='store_true')
    FORMAT = "%(name)s  %(message)s"

    parsed_args = parser.parse_args()
    mpl_logger = logging.getLogger()
    mpl_logger.info("Starting run.....")
    try:
        main(mpl_logger, parsed_args)
    except Exception as e:
        mpl_logger.warning(f'Unexpected exception: {e}', exc_info=True)
        sys.exit(1)
