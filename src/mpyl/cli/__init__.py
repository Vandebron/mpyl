"""Command Line Interface parsing for MPyL"""
import asyncio
import importlib
import logging
from dataclasses import dataclass
from importlib.metadata import version as version_meta
from typing import Optional

import aiohttp
import requests
from aiohttp import ClientConnectorError, ClientTimeout

from rich.console import Console
from rich.logging import RichHandler

from ..utilities.repo import Repository

CONFIG_PATH_HELP = 'Path to the config.yml. Needs to comply with schema at ' \
                   'https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml ' \
                   'Can be set via `MPYL_CONFIG_PATH` env var. '


@dataclass(frozen=True)
class CliContext:
    config: dict
    repo: Repository
    console: Console
    verbose: bool


async def fetch_latest_version() -> Optional[str]:
    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
            async with session.get("https://pypi.org/pypi/mpyl/json") as response:
                body = await response.json()
                return body.get('info', {}).get('version')
    except (asyncio.exceptions.TimeoutError, ClientConnectorError, requests.exceptions.RequestException):
        return None


def get_meta_version():
    try:
        return version_meta('mpyl')
    except importlib.metadata.PackageNotFoundError:
        return None


async def check_updates(meta: str) -> Optional[str]:
    latest = await fetch_latest_version()
    if latest and meta != latest:
        return latest
    return None


def get_version():
    try:
        return f"v{version_meta('mpyl')}"
    except importlib.metadata.PackageNotFoundError:
        return '(local)'


FORMAT = "%(message)s"


def create_console_logger(local: bool, verbose: bool) -> Console:
    console = Console(markup=True, width=None if local else 135, no_color=False, log_path=False, log_time=False,
                      color_system='256')
    logging.basicConfig(
        level="DEBUG" if verbose else "INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True, console=console, show_path=local)]
    )
    return console
