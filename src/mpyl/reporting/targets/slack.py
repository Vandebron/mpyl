""" Slack result reporter. Install https://api.slack.com/apps/A04T5GFMUU8 to create a token with the required
permissions.
"""
import re
from typing import Dict

from slack_sdk import WebClient
from slack_sdk.models.blocks import HeaderBlock, SectionBlock, MarkdownTextObject, ContextBlock

from . import Reporter
from ..formatting.markdown import run_result_to_markdown
from ...steps.run import RunResult


def to_slack_markdown(markdown: str) -> str:
    regex_replace = (
        (re.compile(r'^- ', flags=re.M), '• '),
        (re.compile(r'^  - ', flags=re.M), '  ◦ '),
        (re.compile(r'^    - ', flags=re.M), '    ⬩ '),
        (re.compile(r'^      - ', flags=re.M), '    ◽ '),
        (re.compile(r'^#+ (.+)$', flags=re.M), r'*\1*'),
        (re.compile(r'\*\*'), '*'),
    )
    for regex, replacement in regex_replace:
        markdown = regex.sub(replacement, markdown)
    return markdown


class SlackReporter(Reporter):

    def __init__(self, config: Dict):
        slack_config = config.get('slack')
        if not slack_config:
            raise ValueError('slack config not set')
        self._client = WebClient(token=slack_config['botToken'])

    def send_report(self, results: RunResult) -> None:
        user = self._client.users_lookupByEmail(email='sam@vandebron.nl')
        user_id = user['user']['id']

        build_props = results.run_properties
        details = results.run_properties.details

        context = self.compose_context(build_props, details)

        text = to_slack_markdown(
            run_result_to_markdown(results) + (f'<@{user_id}>' if user_id else ''))

        blocks = [HeaderBlock(text="Master nightly pipeline build results"),
                  SectionBlock(text=MarkdownTextObject(text=text)),
                  ContextBlock(elements=[MarkdownTextObject(text=context)])
                  ]

        self._client.chat_postMessage(channel='#notification-test', icon_emoji=':robot_face:',
                                      mrkdwn=True,
                                      blocks=blocks)

    @staticmethod
    def compose_context(build_props, details) -> str:
        return f"icon Build <{details.run_url}|{details.build_id.upper()}> and changes in " \
               f"<{details.change_url}|{build_props.versioning.identifier.upper()}> " \
               f"started by _{build_props.details.user}_"
