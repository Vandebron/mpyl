"""
Jira result reporter.

### Usage

To determine which `Jira` ticket a pipeline run relates to, the branch is parsed.
The following pattern is assumed `[A-Za-z]{3}-\\d+` to signify the Jira ticket key.
If a Jira ticket key cannot be extracted from the branch, this reporter will fail silently.

### Actions
 - If the ticket is still in its initial stage, it transitioned to the following stage. For example:
`To Do` -> `In progress`
 - If the ticket hasn't been assigned to any particular person, it will be assigned to whoever triggered
 the pipeline run.

### Configuration
Configure hostname and credentials under `jira` in the `config.yml`
"""
import re
from dataclasses import dataclass
from logging import Logger
from typing import Optional

from atlassian import Jira

from . import Reporter
from ...steps.run import RunResult


@dataclass(frozen=True)
class JiraTicket:
    ticket_id: str
    issue_type: str
    summary: str
    description: str
    status_name: str
    user_avatar: str
    user_email: str
    assignee_email: Optional[str]

    @staticmethod
    def from_issue_response(response):
        fields = response['fields']
        assignee = fields.get('assignee')
        user = assignee or fields.get('reporter') or fields.get('creator')
        avatar = user['avatarUrls']['48x48'] if user else ''
        status_name = fields['status']['name']
        assignee_email = assignee['emailAddress'] if assignee else None

        return JiraTicket(ticket_id=response['key'], issue_type=fields['issuetype']['name'], summary=fields['summary'],
                          status_name=status_name, description=fields['description'], user_avatar=avatar,
                          user_email=user['emailAddress'], assignee_email=assignee_email)


def extract_ticket_from_branch(branch: str) -> Optional[str]:
    pattern = r'[A-Za-z]{3}-\d+'
    ticket: Optional[str] = next(iter(re.findall(pattern, branch)), None)
    if ticket:
        return ticket.upper()
    return None


@dataclass(frozen=True)
class JiraConfig:
    site: str
    user_name: str
    password: str

    @staticmethod
    def from_config(config: dict):
        return JiraConfig(site=config['site'], user_name=config['userName'], password=config['password'])


class JiraReporter(Reporter):

    def __init__(self, config: dict, branch: str, logger: Logger):
        jira_config = config.get('jira')
        if not jira_config:
            raise ValueError('jira section needs to be defined in config.yml')
        self._ticket = extract_ticket_from_branch(branch)

        jira_config = JiraConfig.from_config(jira_config)
        self._config = jira_config
        self._jira = Jira(url=jira_config.site, username=jira_config.user_name, password=jira_config.password,
                          api_version='3', cloud=True)
        self._logger = logger

    def send_report(self, results: RunResult) -> None:
        if not self._ticket:
            return None

        issue_response = self._jira.get_issue(self._ticket)
        ticket = JiraTicket.from_issue_response(issue_response)

        self.__move_ticket_forward(ticket)

        user_email = results.run_properties.details.user_email
        if user_email:
            self.__assign_ticket(user_email, ticket)
        return None

    def __assign_ticket(self, run_user_email: str, ticket: JiraTicket):
        if ticket.assignee_email is None or ticket.assignee_email != run_user_email:
            jira_user = self._jira.user_find_by_user_string(query=run_user_email)
            if jira_user:
                account_id = jira_user.pop().get('accountId')
                self._logger.info(f'Assigning {ticket.ticket_id} to {account_id}')
                self._jira.assign_issue(self._ticket, account_id=account_id)

    def __move_ticket_forward(self, ticket: JiraTicket):
        transitions = self._jira.get_issue_transitions(self._ticket)
        for idx, transition in enumerate(transitions):
            if transition['name'] == ticket.status_name:
                if idx == 0:
                    target_state = transitions[idx + 1]['name']
                    self._logger.info(f'Moving {ticket.ticket_id} to {target_state}')
                    self._jira.issue_transition(self._ticket, target_state)
