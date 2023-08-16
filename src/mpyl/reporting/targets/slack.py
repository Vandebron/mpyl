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
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackClientError, SlackApiError
from slack_sdk.models.blocks import (
    HeaderBlock,
    SectionBlock,
    MarkdownTextObject,
    ContextBlock,
    ImageElement,
    Block,
)

from . import Reporter, ReportOutcome
from ..formatting.markdown import run_result_to_markdown
from ...steps.models import RunProperties
from ...steps.run import RunResult


def to_slack_markdown(markdown: str) -> str:
    regex_replace = (
        (re.compile(r"\[(.*?)\]\((.*?)\)"), r"<\2|\1>"),
        (re.compile(r"^- ", flags=re.M), "• "),
        (re.compile(r"^  - ", flags=re.M), "  ◦ "),
        (re.compile(r"^    - ", flags=re.M), "    ⬩ "),
        (re.compile(r"^      - ", flags=re.M), "    ◽ "),
        (re.compile(r"^#+ (.+)$", flags=re.M), r"*\1*"),
        (re.compile(r"\*\*"), "*"),
        (re.compile(r"~~"), "~"),
    )
    for pattern, replacement in regex_replace:
        markdown = re.sub(pattern, replacement, markdown)
    return markdown


@dataclass(frozen=True)
class SlackIcons:
    building: str
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


class SlackOutcome(ReportOutcome):
    pass


class SlackReporter(Reporter):
    _icons: SlackIcons
    _message_identifier: Optional[MessageIdentifier]

    def __init__(
        self,
        config: dict,
        channel: Optional[str],
        versioning_identifier: str,
        target: str,
        message_identifier: Optional[MessageIdentifier] = None,
    ):
        slack_config = config.get("slack")
        if not slack_config:
            raise ValueError("slack config not set")
        self._client = WebClient(token=slack_config["botToken"])
        self._channel = channel
        self._title = f"MPyL run for {versioning_identifier} on {target}"
        icons = slack_config["icons"]
        self._icons = SlackIcons(
            success=icons["success"],
            failure=icons["failure"],
            building=icons["building"],
        )
        self._message_identifier = message_identifier

    def send_report(
        self, results: RunResult, text: Optional[str] = None
    ) -> ReportOutcome:
        try:
            email = results.run_properties.details.user_email
            user_info = self.__get_user_info(email)

            if not self._channel and user_info.initiator:
                self._channel = self.__open_conversation_with_user(user_info.initiator)

            if not self._channel:
                return SlackOutcome(
                    success=False,
                    exception=ValueError(
                        f"Channel not explicitly set and initiator for {email} could not be determined"
                    ),
                )

            body = to_slack_markdown(text if text else run_result_to_markdown(results))
            blocks = self.__compose_blocks(results, body, user_info)

            if self._message_identifier:
                self._client.chat_update(
                    channel=self._message_identifier.channel_id,
                    ts=self._message_identifier.time_stamp,
                    icon_emoji=":robot_face:",
                    mrkdwn=True,
                    blocks=blocks,
                    text=body,
                )
                return SlackOutcome(success=True)

            response = self._client.chat_postMessage(
                channel=self._channel,
                icon_emoji=":robot_face:",
                mrkdwn=True,
                blocks=blocks,
                text=body,
            )
            self._message_identifier = MessageIdentifier(
                channel_id=response["channel"], time_stamp=response["ts"]
            )
            return SlackOutcome(success=True)
        except SlackClientError as slack_exception:
            return SlackOutcome(success=False, exception=slack_exception)

    def send_progress_update(self, results: RunResult, text: Optional[str]):
        if not self._message_identifier:
            raise ValueError(
                "Message identifier not set. Cannot call update before `send_report` has been called"
            )

        result_markdown = text if text else run_result_to_markdown(results)
        body = to_slack_markdown(result_markdown)
        blocks = self.__compose_blocks(
            results,
            body,
            self.__get_user_info(results.run_properties.details.user_email),
        )
        self._client.chat_update(
            channel=self._message_identifier.channel_id,
            ts=self._message_identifier.time_stamp,
            icon_emoji=":robot_face:",
            mrkdwn=True,
            blocks=blocks,
            text=body,
        )

    def __open_conversation_with_user(self, user_id: str):
        opened_channel = self._client.conversations_open(users=[user_id])
        return opened_channel["channel"]["id"]

    def __get_user_info(self, user_email: Optional[str]):
        profile_data: dict[str, str] = {}
        user_id = None
        if user_email:
            try:
                user = self._client.users_lookupByEmail(email=user_email)
                user_id = user["user"]["id"]
                resp = self._client.users_profile_get(user=user_id)
                profile_data = resp.get("profile", {})
            except SlackApiError:
                profile_data = {}

        return UserInfo(
            user_name=profile_data.get("real_name_normalized", "Anonymous"),
            profile_image=profile_data.get(
                "image_24", "https://avatars.githubusercontent.com/u/18010732"
            ),
            initiator=user_id,
        )

    def __get_icon(self, results: RunResult):
        if results.is_in_progress:
            return self._icons.building
        if results.is_success:
            return self._icons.success
        return self._icons.failure

    def __compose_blocks(
        self, results: RunResult, text: str, user_info: UserInfo
    ) -> list[Block]:
        icon = self.__get_icon(results)

        context = self.compose_context(
            results.run_properties, icon, user_info.user_name
        )
        return [
            HeaderBlock(text=self._title),
            SectionBlock(text=MarkdownTextObject(text=text)),
            ContextBlock(
                elements=[
                    MarkdownTextObject(text=context),
                    ImageElement(
                        image_url=user_info.profile_image, alt_text=user_info.user_name
                    ),
                ]
            ),
        ]

    @staticmethod
    def compose_context(
        build_props: RunProperties, icon: str, user: Optional[str]
    ) -> str:
        details = build_props.details
        user_name = user if user else details.user
        return (
            f":{icon}: Build <{details.run_url}|{details.build_id.upper()}> for "
            f"<{details.change_url}|{build_props.versioning.identifier.upper()}> "
            f"started by _{user_name}_"
        )
