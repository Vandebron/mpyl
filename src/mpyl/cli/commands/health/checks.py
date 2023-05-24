"""Health checks"""

import asyncio
import os
import pkgutil
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


def perform_health_checks(console: Console):
    console.print(Markdown('*Version*'))
    __check_version(console)

    console.print(Markdown('*MPyL configuration*'))
    __check_config(console, env_var='MPYL_CONFIG_PATH', default='mpyl_config.yml',
                   schema_path='../../../schema/mpyl_config.schema.yml', name='config')

    console.print(Markdown('*Run configuration*'))
    __check_config(console, env_var='MPYL_RUN_PROPERTIES_PATH', default=DEFAULT_RUN_PROPERTIES_FILE_NAME,
                   schema_path='../../../schema/run_properties.schema.yml', name='run properties')

    console.print(Markdown('*Jenkins*'))
    __check_jenkins(console)


def __check_jenkins(console):
    path = os.environ.get('MPYL_CONFIG_PATH', default=DEFAULT_CONFIG_FILE_NAME)
    if not os.path.exists(path):
        console.log(f'  ❌ Configuration not found at: {path}')
        return

    parsed = parse_config(path)

    try:
        jenkins_conf = JenkinsConfig.from_config(parsed)
        console.log(f'  ✅ Jenkins configured for pipeline `{jenkins_conf.default_pipeline}` at {jenkins_conf.url}')
    except KeyError as exc:
        console.log(f'  ❌ Jenkins config not valid: {exc}')

    try:
        get_token(GithubConfig(parsed))
        console.log('  ✅ Github token found')
    except CalledProcessError:
        console.log('  ❌ Github token not found. Install Github CLI `brew install gh`')

    if os.environ.get('JENKINS_USER'):
        console.log('  ✅ Jenkins user set')
    else:
        console.log("  ❌ Jenkins user not set via JENKINS_USER env var")
        jenkins_url = f'{JenkinsConfig.from_config(parsed).url}user/me@vandebron.nl/configure'
        console.log(f"     Create a user API token in Jenkins (user:password) API token: {jenkins_url}")

    if os.environ.get('JENKINS_PASSWORD'):
        console.log('  ✅ Jenkins password set')
    else:
        console.log("  ❌ Jenkins password not set via JENKINS_PASSWORD env var")


def __check_version(console):
    update = asyncio.get_event_loop().run_until_complete(fetch_latest_version())
    meta_version = get_meta_version()
    if update and meta_version:
        if meta_version == update:
            console.log(f'  ✅ At latest version: {update}')
        else:
            console.log(f'  ❌ Outdated version: {meta_version} (latest: {update})')
    else:
        console.log('  ❌ Could not determine latest version')


def __check_config(console, env_var, default, schema_path, name):
    path = os.environ.get(env_var, default=default)
    location = f"{name} at '/{path}' via environment variable '{env_var}'" if os.environ.get(
        env_var) else f"{name} at '/{path}'"
    if os.path.exists(path):
        console.log(f"  ✅ Found {location}")

        if load_dotenv(Path(".env")):
            console.log("  ✅ Set env variables via .env file")

        parsed = parse_config(path)
        schema_dict = pkgutil.get_data(__name__, schema_path)
        if schema_dict:
            try:
                validate(parsed, schema_dict.decode('utf-8'))
                console.log(f'  ✅ {name.capitalize()} is valid')
            except jsonschema.exceptions.ValidationError as exc:
                console.log(f"  ❌ {name.capitalize()} is invalid: {exc.message} at '{'.'.join(exc.path)}'")
    else:
        console.log(f"  ❌ Could not find {location}. Location can be specified with env var '{env_var}'")
