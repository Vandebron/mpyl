"""Health checks"""

import asyncio
import os
import pkgutil
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional

import jsonschema
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from ..build.jenkins import get_token
from ....cli import get_latest_publication, get_meta_version
from ....constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from ....projects.versioning import (
    check_upgrade_needed,
    CONFIG_UPGRADERS,
    pretty_print,
    Upgrader,
    upgrade_file,
    PROJECT_UPGRADERS,
)
from ....utilities.github import GithubConfig
from ....utilities.jenkins import JenkinsConfig
from ....utilities.pyaml_env import parse_config
from ....validation import validate


class HealthConsole:
    def __init__(self, console: Console):
        self.console = console

    def title(self, title: str):
        self.console.print(Markdown(f"*{title}*"))

    def check(self, check: str, success: bool):
        icon = "✅" if success else "❌"
        self.console.print(Markdown(f"&nbsp;&nbsp;{icon} {check}"))

    def print(self, text: str):
        self.console.print(Markdown(text))


def perform_health_checks(
    bare_console: Console, is_ci: bool = False, perform_upgrade: bool = False
):
    console = HealthConsole(bare_console)
    load_dotenv(Path(".env"))

    console.title("Version")
    __check_version(console)

    console.title("MPyL configuration")
    if config_path := __validate_config_path(
        console,
        env_var="MPYL_CONFIG_PATH",
        default=DEFAULT_CONFIG_FILE_NAME,
        config_name="config",
    ):
        __validate_config(
            console,
            config_file_path=config_path,
            schema_path="../../../schema/mpyl_config.schema.yml",
            upgraders=CONFIG_UPGRADERS,
            perform_upgrade=perform_upgrade,
        )

    console.title("Run configuration")
    if properties_path := __validate_config_path(
        console,
        env_var="MPYL_RUN_PROPERTIES_PATH",
        default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
        config_name="run properties",
    ):
        __validate_config(
            console,
            config_file_path=properties_path,
            schema_path="../../../schema/run_properties.schema.yml",
            upgraders=PROJECT_UPGRADERS,
            perform_upgrade=perform_upgrade,
        )

    if not is_ci:
        console.title("Jenkins")
        __check_jenkins(console)


def __check_jenkins(console: HealthConsole):
    path = os.environ.get("MPYL_CONFIG_PATH", default=DEFAULT_CONFIG_FILE_NAME)
    if not os.path.exists(path):
        console.check(f"Configuration not found at: `{path}`", success=False)
        return

    parsed = parse_config(Path(path))

    try:
        jenkins_conf = JenkinsConfig.from_config(parsed)
        console.check(
            f"Jenkins configured for pipeline `{jenkins_conf.default_pipeline}` "
            f"at [{jenkins_conf.url}]({jenkins_conf.url})",
            success=True,
        )
    except KeyError as exc:
        console.check(f"Jenkins not (correctly) configured: {exc}", success=False)
        return

    gh_is_installed = shutil.which("gh")
    if gh_is_installed:
        console.check("Github cli client `gh` installed", success=True)
    else:
        console.check(
            "Github cli client `gh` not found. Install via [https://cli.github.com/](https://cli.github.com/) "
            "and run `gh auth login`",
            success=False,
        )

    if gh_is_installed:
        try:
            get_token(GithubConfig.from_config(parsed))
            console.check("Github token found", success=True)
        except KeyError:
            console.check(
                "Config invalid, cannot determine github configuration", success=False
            )
        except CalledProcessError:
            console.check(
                "Github token not found. Log in with `gh auth login`", success=False
            )

    if os.environ.get("JENKINS_USER"):
        console.check("Jenkins user set", success=True)
    else:
        jenkins_url = (
            f"{JenkinsConfig.from_config(parsed).url}user/me@vandebron.nl/configure"
        )
        message = (
            f"Jenkins user not set via JENKINS_USER env var. Create a user API token in Jenkins"
            f" (user:password) API token: {jenkins_url}"
        )
        console.check(message, success=False)

    if os.environ.get("JENKINS_PASSWORD"):
        console.check("Jenkins password set", success=True)
    else:
        console.check(
            "Jenkins password not set via JENKINS_PASSWORD env var", success=False
        )


def __check_version(console):
    update = asyncio.get_event_loop().run_until_complete(get_latest_publication())
    meta_version = get_meta_version()
    if update and meta_version:
        if meta_version == update:
            console.check(f"At latest version: {update}", success=True)
        else:
            console.check(
                f"Outdated version: {meta_version} (latest: {update})", success=False
            )
    else:
        console.check("Could not determine latest version", success=False)


def __validate_config_path(
    console: HealthConsole, env_var: str, default: str, config_name: str
) -> Optional[Path]:
    path_env = os.environ.get(env_var)
    path = Path(path_env or default)
    location = (
        f"{config_name} at `{path}` via environment variable `{env_var}`"
        if path_env
        else f"{config_name} at `{path}`"
    )
    if os.path.exists(path):
        console.check(f"Found {location}", success=True)
        return path

    console.check(
        f"Could not find {location}. Location can be specified with env var '{env_var}'",
        success=False,
    )
    return None


def __validate_config(
    console: HealthConsole,
    config_file_path: Path,
    schema_path: str,
    upgraders: list[Upgrader],
    perform_upgrade: bool = False,
):
    path, diff = check_upgrade_needed(config_file_path, upgraders)
    pretty_diff = pretty_print(diff) if diff else ""
    if pretty_diff == "":
        console.check("Upgrade not necessary", success=True)
    else:
        console.check("Upgrade required", success=False)
        console.print("Expected changes:")
        console.print(pretty_diff)
        if perform_upgrade or (sys.stdout.isatty() and Confirm.ask("Upgrade now?")):
            upgraded = upgrade_file(path, upgraders)
            if upgraded:
                path.write_text(upgraded, encoding="utf-8")
                console.check(
                    "Upgrade successful. You may need to run `mpyl projects upgrade` still.",
                    success=True,
                )
            else:
                console.check("Could not upgrade", success=False)

    if load_dotenv(Path(".env")):
        console.check("Set env variables via .env file", success=True)

    parsed = parse_config(path)
    schema_dict = pkgutil.get_data(__name__, schema_path)
    if schema_dict:
        try:
            validate(parsed, schema_dict.decode("utf-8"))
            console.check(f"{config_file_path} is valid", success=True)
        except jsonschema.exceptions.ValidationError as exc:
            console.check(
                f"{config_file_path} is invalid: {exc.message} at '{'.'.join(map(str, exc.path))}'."
                f" 🤔 Did you rebase your branch onto {parsed.get('vcs', {}).get('git', {}).get('mainBranch')}?",
                success=False,
            )
