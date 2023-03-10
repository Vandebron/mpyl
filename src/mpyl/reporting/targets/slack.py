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
from slack_sdk.models.blocks import HeaderBlock, SectionBlock, MarkdownTextObject, ContextBlock, ImageElement, Block

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
        (re.compile(r'~~'), '~'),
    )
    for regex, replacement in regex_replace:
        markdown = regex.sub(replacement, markdown)
    return markdown


@dataclass(frozen=True)
class SlackIcons:
    success: str
    failure: str


@dataclass(frozen=True)
class MessageIdentifier:
    channel_id: str
    time_stamp: str


@dataclass(frozen=True)
class UserInfo:
    user_name: str
    profile_image: str
    initiator: Optional[str]


class SlackReporter(Reporter):
    _icons: SlackIcons
    _message_identifier: Optional[MessageIdentifier]

    def __init__(self, config: Dict, channel: Optional[str], title: str,
                 message_identifier: Optional[MessageIdentifier] = None):
        slack_config = config.get('slack')
        if not slack_config:
            raise ValueError('slack config not set')
        self._client = WebClient(token=slack_config['botToken'])
        self._channel = channel
        self._title = title
        icons = slack_config['icons']
        self._icons = SlackIcons(success=icons['success'], failure=icons['failure'])
        self._message_identifier = message_identifier

    def send_report(self, results: RunResult) -> None:
        user_info = self.__get_user_info(results.run_properties.details.user_email)

        if not self._channel and user_info.initiator:
            self._channel = self.__open_conversation_with_user(user_info.initiator)

        if not self._channel:
            raise ValueError('Channel not explicitly set and initiator could not be determined')

        text = to_slack_markdown(run_result_to_markdown(results))
        blocks = self.__compose_blocks(results, text, user_info)

        if self._message_identifier:
            self._client.chat_update(channel=self._message_identifier.channel_id,
                                     ts=self._message_identifier.time_stamp,
                                     icon_emoji=':robot_face:', mrkdwn=True, blocks=blocks, text=text)
            return

        response = self._client.chat_postMessage(channel=self._channel, icon_emoji=':robot_face:', mrkdwn=True,
                                                 blocks=blocks, text=text)
        self._message_identifier = MessageIdentifier(channel_id=response['channel'], time_stamp=response['ts'])

    def __open_conversation_with_user(self, user_id: str):
        opened_channel = self._client.conversations_open(users=[user_id])
        return opened_channel['channel']['id']

    def __get_user_info(self, user_email: Optional[str]):
        profile_data: dict[str, str] = {}
        user_id = None
        if user_email:
            user = self._client.users_lookupByEmail(email=user_email)
            user_id = user['user']['id']
            resp = self._client.users_profile_get(user=user_id)
            profile_data = resp.get('profile', {})

        return UserInfo(user_name=profile_data.get('real_name_normalized', 'Anonymous'),
                        profile_image=profile_data.get('image_24',
                                                       'https://avatars.githubusercontent.com/u/18010732'),
                        initiator=user_id)

    def __compose_blocks(self, results: RunResult, text: str, user_info: UserInfo) -> list[Block]:
        icon = self._icons.success if results.is_success else self._icons.failure
        context = self.compose_context(results.run_properties, icon, user_info.user_name)
        return [HeaderBlock(text=self._title),
                SectionBlock(text=MarkdownTextObject(text=text)),
                ContextBlock(elements=[MarkdownTextObject(text=context),
                                       ImageElement(image_url=user_info.profile_image, alt_text=user_info.user_name)])
                ]

    @staticmethod
    def compose_context(build_props: RunProperties, icon: str, user: Optional[str]) -> str:
        details = build_props.details
        user_name = user if user else details.user
        return f":{icon}: Build <{details.run_url}|{details.build_id.upper()}> and changes in " \
               f"<{details.change_url}|{build_props.versioning.identifier.upper()}> " \
               f"started by _{user_name}_"
