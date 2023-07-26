"""Health checks"""

import asyncio
import os
import pkgutil
import shutil
from pathlib import Path
from subprocess import CalledProcessError

import jsonschema
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from ..build.jenkins import get_token
from ....constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from ....utilities.github import GithubConfig
from ....utilities.jenkins import JenkinsConfig
from ....utilities.pyaml_env import parse_config
from ....cli import fetch_latest_version, get_meta_version
from ....validation import validate


class HealthConsole:
    def __init__(self, console: Console):
        self.console = console

    def title(self, title: str):
        self.console.print(Markdown(f"*{title}*"))

    def check(self, check: str, success: bool):
        icon = "✅" if success else "❌"
        self.console.print(Markdown(f"&nbsp;&nbsp;{icon} {check}"))


def perform_health_checks(bare_console: Console, is_ci: bool = False):
    console = HealthConsole(bare_console)
    load_dotenv(Path(".env"))

    console.title("Version")
    __check_version(console)

    console.title("MPyL configuration")
    __check_config(
        console,
        env_var="MPYL_CONFIG_PATH",
        default=DEFAULT_CONFIG_FILE_NAME,
        schema_path="../../../schema/mpyl_config.schema.yml",
        name="config",
    )

    console.title("Run configuration")
    __check_config(
        console,
        env_var="MPYL_RUN_PROPERTIES_PATH",
        default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
        schema_path="../../../schema/run_properties.schema.yml",
        name="run properties",
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
    update = asyncio.get_event_loop().run_until_complete(fetch_latest_version())
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


def __check_config(console, env_var, default, schema_path, name):
    path_env = os.environ.get(env_var)
    path = path_env or default
    location = (
        f"{name} at `/{path}` via environment variable `{env_var}`"
        if path_env
        else f"{name} at `/{path}`"
    )
    if os.path.exists(path):
        console.check(f"Found {location}", success=True)

        if load_dotenv(Path(".env")):
            console.check("Set env variables via .env file", success=True)

        parsed = parse_config(path)
        schema_dict = pkgutil.get_data(__name__, schema_path)
        if schema_dict:
            try:
                validate(parsed, schema_dict.decode("utf-8"))
                console.check(f"{name.capitalize()} is valid", success=True)
            except jsonschema.exceptions.ValidationError as exc:
                console.check(
                    f"{name.capitalize()} is invalid: {exc.message} at '{'.'.join(exc.path)}'. 🤔Did you rebase"
                    f" your branch onto {parsed['cvs']['git']['mainBranch']}?",
                    success=False,
                )
    else:
        console.check(
            f"Could not find {location}. Location can be specified with env var '{env_var}'",
            success=False,
        )
