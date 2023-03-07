""" Slack result reporter. Install https://api.slack.com/apps/A04T5GFMUU8 to create a token with the required
permissions.
Use either the suggested app, or create your own with the following settings:
```yaml
display_information:
  name: MPyL
  description: CI/CD pipeline
  background_color: "#2f6327"
features:
  bot_user:
    display_name: MPyL
    always_online: false
oauth_config:
  scopes:
    bot:
      - users.profile:read
      - chat:write
      - files:write
      - reactions:write
      - users:read
      - users:read.email
      - channels:join
      - groups:write
      - im:write
      - mpim:write
      - channels:manage
settings:
  org_deploy_enabled: true
  socket_mode_enabled: false
  token_rotation_enabled: false
```
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional

from slack_sdk import WebClient
from slack_sdk.models.blocks import HeaderBlock, SectionBlock, MarkdownTextObject, ContextBlock, ImageElement

from . import Reporter
from ..formatting.markdown import run_result_to_markdown
from ...steps.models import RunProperties
from ...steps.run import RunResult


def to_slack_markdown(markdown: str) -> str:
    regex_replace = (
        (re.compile(r'\[(.*)\]\((.*)\)', flags=re.M), r'<\2|\1>'),
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


@dataclass(frozen=True)
class SlackIcons:
    success: str
    failure: str


class SlackReporter(Reporter):
    _icons: SlackIcons

    def __init__(self, config: Dict, channel: str, title: str):
        slack_config = config.get('slack')
        if not slack_config:
            raise ValueError('slack config not set')
        self._client = WebClient(token=slack_config['botToken'])
        self._channel = channel
        self._title = title
        icons = slack_config['icons']
        self._icons = SlackIcons(success=icons['success'], failure=icons['failure'])

    def send_report(self, results: RunResult) -> None:
        build_props = results.run_properties

        icon = self._icons.success if results.is_success else self._icons.failure

        user_email = build_props.details.user_email
        initiator = ''
        profile_data: dict[str, str] = {}
        if user_email:
            user = self._client.users_lookupByEmail(email=user_email)
            user_id = user['user']['id']
            if not results.is_success:
                initiator = f'<@{user_id}>'

            resp = self._client.users_profile_get(user=user_id)
            profile_data = resp.get('profile', {})

        user_name = profile_data.get('real_name_normalized', 'Anonymous')
        profile_image = profile_data.get('image_24', 'https://avatars.githubusercontent.com/u/18010732')

        context = self.compose_context(build_props, icon, user_name)
        text = to_slack_markdown(run_result_to_markdown(results) + initiator)
        blocks = [HeaderBlock(text=self._title),
                  SectionBlock(text=MarkdownTextObject(text=text)),
                  ContextBlock(elements=[MarkdownTextObject(text=context),
                                         ImageElement(image_url=profile_image, alt_text=user_name)])
                  ]

        self._client.chat_postMessage(channel=self._channel, icon_emoji=':robot_face:', mrkdwn=True, blocks=blocks,
                                      text=text)

    @staticmethod
    def compose_context(build_props: RunProperties, icon: str, user: Optional[str]) -> str:
        details = build_props.details
        user_name = user if user else details.user
        return f":{icon}: Build <{details.run_url}|{details.build_id.upper()}> and changes in " \
               f"<{details.change_url}|{build_props.versioning.identifier.upper()}> " \
               f"started by _{user_name}_"
