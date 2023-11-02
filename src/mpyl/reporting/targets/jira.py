"""
Jira result reporter.

### Usage

To determine which `Jira` ticket a pipeline run relates to, the branch is parsed.
The following pattern is assumed unless otherwise specified: `[A-Za-z]{3,}-` to signify the Jira ticket key.
If a Jira ticket key cannot be extracted from the branch, this reporter will fail silently.

### Actions
 - If the ticket is still in its initial stage, it transitioned to the following stage. For example:
`To Do` -> `In progress`
 - If the ticket hasn't been assigned to any particular person, it will be assigned to whoever triggered
 the pipeline run.

### Configuration
Configure hostname and credentials under `jira` in the `config.yml`

.. note:: Use API token as password
   You need to create a regular Jira account to represent the MPyL system integration.
   The username is the email address of the account. Log in as this user and create an
   [API token](https://id.atlassian.com/manage-profile/security/api-tokens) to be used as the password.
"""
import re
from dataclasses import dataclass
from logging import Logger
from re import Pattern
from typing import Optional
from urllib.parse import urlsplit

import requests
from atlassian import Jira

from . import Reporter, ReportOutcome
from ..formatting.markdown import markdown_for_stage
from ...constants import DEFAULT_CONFIG_FILE_NAME
from ...steps import deploy
from ...steps.run import RunResult


@dataclass(frozen=True)
class JiraTicket:
    jira_url: str
    ticket_id: str
    ticket_url: str
    issue_type: str
    issue_hierarchy: int  # level 1 - Epic, level 0 - Story, level -1 - Sub-task
    summary: str
    description: str
    status_name: str
    user_avatar: str
    user_email: str
    assignee_email: Optional[str]

    @staticmethod
    def from_issue_response(response):
        jira_url = "{uri.scheme}://{uri.netloc}".format(uri=urlsplit(response["self"]))
        fields = response["fields"]
        ticket_id = response["key"]
        assignee = fields.get("assignee")
        user = assignee or fields.get("reporter") or fields.get("creator")
        avatar = user["avatarUrls"]["24x24"] if user else ""
        status_name = fields["status"]["name"]
        assignee_email = assignee["emailAddress"] if assignee else None
        ticket_url = f"{jira_url}/browse/{ticket_id}"

        return JiraTicket(
            jira_url=jira_url,
            ticket_id=ticket_id,
            ticket_url=ticket_url,
            issue_type=fields["issuetype"]["name"],
            issue_hierarchy=fields["issuetype"]["hierarchyLevel"],
            summary=fields["summary"],
            status_name=status_name,
            description=fields["description"],
            user_avatar=avatar,
            user_email=user["emailAddress"],
            assignee_email=assignee_email,
        )


def extract_ticket_from_branch(branch: str, pattern: Pattern) -> Optional[str]:
    ticket: Optional[str] = next(iter(re.findall(pattern, branch)), None)
    if ticket:
        return ticket.upper()
    return None


@dataclass(frozen=True)
class JiraConfig:
    site: str
    user_name: str
    password: str
    ticket_pattern: Pattern
    token: Optional[str]

    @staticmethod
    def from_config(config: dict):
        jira_config = config.get("jira")
        if not jira_config:
            raise KeyError(
                f"jira section needs to be defined in {DEFAULT_CONFIG_FILE_NAME}"
            )
        return JiraConfig(
            site=jira_config["site"],
            user_name=jira_config["userName"],
            password=jira_config["password"],
            ticket_pattern=re.compile(
                jira_config.get("ticketPattern", "[A-Za-z]{2,}-\\d+")
            ),
            token=jira_config.get("token"),
        )


def create_jira_for_config(jira_config: JiraConfig):
    return (
        Jira(url=jira_config.site, token=jira_config.token, api_version="2", cloud=True)
        if jira_config.token
        else Jira(
            url=jira_config.site,
            username=jira_config.user_name,
            password=jira_config.password,
            api_version="2",
            cloud=True,
        )
    )


def to_github_markdown(jira_markdown: str, jira_url: str) -> str:
    jira_markdown = re.sub(
        r"\[(.*)/(.*)\|(.*)\|smart-link\]", r"[\2](\3)", jira_markdown
    )
    jira_markdown = re.sub(r"\[(.*)\|(.*)\]", r"[\1](\2)", jira_markdown)
    jira_markdown = re.sub(
        r"\[~accountid:(.*)\]", rf"[👩‍💻]({jira_url}/jira/people/\1)", jira_markdown
    )
    jira_markdown = re.sub(r"\{\{(.*)\}\}", r"`\1`", jira_markdown)
    jira_markdown = re.sub(r"\{quote}(.*)\{quote}", r"> \1", jira_markdown)
    jira_markdown = re.sub(
        r"\{noformat\}((.|\n)*)\{noformat\}", r"```\n\1\n```", jira_markdown
    )
    jira_markdown = re.sub(
        r"\{code:+(.*)\}((.|\n)*)\{code\}", r"```\1\n\2\n```", jira_markdown
    )
    jira_markdown = re.sub(r"\{noformat\}((.|\n)*)", r"```\n\1\n```", jira_markdown)
    jira_markdown = re.sub(r"\*(.*)\*", r"**\1**", jira_markdown)
    jira_markdown = re.sub(r"_(.*)_", r"*\1*", jira_markdown)
    jira_markdown = re.sub(r"!.*\|.*!", r"", jira_markdown)

    jira_markdown = jira_markdown.replace("# ", "- ")
    jira_markdown = jira_markdown.replace("h1. ", "### ")
    jira_markdown = jira_markdown.replace("h2. ", "#### ")
    jira_markdown = jira_markdown.replace("h3. ", "##### ")
    jira_markdown = jira_markdown.replace("h4. ", "###### ")
    jira_markdown = jira_markdown.replace("h5. ", "###### ")
    jira_markdown = jira_markdown.replace("h6. ", "###### ")
    return jira_markdown


def to_markdown_summary(ticket: JiraTicket, run_result: RunResult) -> str:
    description_markdown = (
        to_github_markdown(ticket.description, ticket.ticket_url)
        if ticket.description
        else ""
    )
    lines = description_markdown.splitlines()
    max_message_length = 288
    if len(lines) > max_message_length:
        description_markdown = "\n".join(lines[:max_message_length]) + "\n..."

    properties = run_result.run_properties
    details = properties.details

    stage_markdown = markdown_for_stage(
        run_result, properties.to_stage(deploy.STAGE_NAME)
    )
    build_status = (
        f"🏗️ Build [{details.build_id}]({details.run_url}) {run_result.status_line}, "
        f"started by _{details.user}_  \n{stage_markdown}"
    )
    return (
        f"### 📕 [{ticket.ticket_id}]({ticket.ticket_url}) {ticket.summary} "
        f'<img src="{ticket.user_avatar}" width="24" height="24" alt="{ticket.user_email}" /> \n'
        f"{description_markdown}\n\n"
        f"{build_status}"
    )


def compose_build_status(result: RunResult, config: dict) -> str:
    jira_config = JiraConfig.from_config(config=config)
    jira_client = create_jira_for_config(jira_config)
    branch = result.run_properties.versioning.branch
    if not branch:
        return " # ⚠️ `versioning.branch` not set, cannot find corresponding ticket"
    ticket_id = extract_ticket_from_branch(branch, jira_config.ticket_pattern)
    if not ticket_id:
        return (
            f" # ⚠️ Could not find ticket corresponding to `{branch}. "
            f"Does your branch name follow the correct pattern?"
        )
    try:
        issue = jira_client.get_issue(ticket_id)
    except requests.exceptions.HTTPError:
        return f" # ⚠️ Could not find jira ticket with id {ticket_id}"
    jira_ticket = JiraTicket.from_issue_response(issue)
    return to_markdown_summary(jira_ticket, result)


class JiraOutcome(ReportOutcome):
    pass


class JiraReporter(Reporter):
    def __init__(self, config: dict, branch: str, logger: Logger):
        jira_config = JiraConfig.from_config(config)
        self._ticket = (
            extract_ticket_from_branch(branch, jira_config.ticket_pattern)
            if branch
            else None
        )
        self._config = jira_config
        self._jira = create_jira_for_config(jira_config)
        self._logger = logger

    def send_report(
        self, results: RunResult, text: Optional[str] = None
    ) -> JiraOutcome:
        if not self._ticket:
            return JiraOutcome(success=True)

        try:
            issue_response = self._jira.get_issue(self._ticket)

            ticket = JiraTicket.from_issue_response(issue_response)

            self.__move_ticket_forward(ticket)

            user_email = results.run_properties.details.user_email
            if user_email and ticket.issue_hierarchy < 1:
                self.__assign_ticket(user_email, ticket)
            return JiraOutcome(success=True)

        except requests.exceptions.HTTPError as exc:
            self._logger.warning(f"Could not handle Jira ticket {self._ticket}: {exc}")
            return JiraOutcome(success=False, exception=exc)

    def __assign_ticket(self, run_user_email: str, ticket: JiraTicket):
        if ticket.assignee_email is None:
            jira_user = self._jira.user_find_by_user_string(query=run_user_email)
            if jira_user:
                account_id = jira_user.pop().get("accountId")
                self._logger.info(f"Assigning {ticket.ticket_id} to {account_id}")
                self._jira.assign_issue(self._ticket, account_id=account_id)

    def __move_ticket_forward(self, ticket: JiraTicket):
        if ticket.status_name == "To Do" and ticket.issue_type != "Epic":
            target_state = "In Progress"
            self._logger.info(f"Moving {ticket.ticket_id} to {target_state}")
            self._jira.issue_transition(self._ticket, target_state)
