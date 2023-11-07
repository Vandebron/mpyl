"""Command Line Interface parsing for MPyL"""
import asyncio
import importlib
import logging
from dataclasses import dataclass
from importlib.metadata import version as version_meta
from pathlib import Path
from typing import Optional

import aiohttp
import click
import requests
from aiohttp import ClientConnectorError, ClientTimeout
from click import BadParameter
from rich.console import Console
from rich.logging import RichHandler

from ..utilities.pyaml_env import parse_config
from ..utilities.repo import Repository

CONFIG_PATH_HELP = "Path to the config.yml. Can be set via `MPYL_CONFIG_PATH` env var. "


@dataclass(frozen=True)
class CliContext:
    config: dict
    repo: Repository
    console: Console
    verbose: bool
    run_properties: dict


@dataclass(frozen=True)
class MpylCliParameters:
    local: bool = False
    tag: Optional[str] = None
    pull_main: bool = False
    verbose: bool = False
    all: bool = False
    stage: Optional[str] = None
    projects: Optional[str] = None


async def get_publication_info(test: bool = False) -> dict:
    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
            async with session.get(
                f"https://{'test.' if test else ''}pypi.org/pypi/mpyl/json"
            ) as response:
                return await response.json()
    except (
        asyncio.exceptions.TimeoutError,
        asyncio.exceptions.CancelledError,
        ClientConnectorError,
        requests.exceptions.RequestException,
    ):
        return {}


async def get_latest_publication(test: bool = False) -> Optional[str]:
    body = await get_publication_info(test)
    return body.get("info", {}).get("version", None)


async def get_release_url(release: str, test: bool = False) -> Optional[str]:
    body = await get_publication_info(test)
    releases = body.get("releases", {})
    if release in releases:
        return releases[release][0].get("url", None)
    return None


def get_meta_version():
    try:
        return version_meta("mpyl")
    except importlib.metadata.PackageNotFoundError:
        return None


async def check_updates(meta: str) -> Optional[str]:
    latest = await get_latest_publication()
    if latest and meta != latest:
        return latest
    return None


def get_version():
    try:
        return f"{version_meta('mpyl')}"
    except importlib.metadata.PackageNotFoundError:
        return "(local)"


FORMAT = "%(message)s"


def create_console_logger(
    show_path: bool, verbose: bool, max_width: Optional[int] = None
) -> Console:
    console = Console(
        markup=True,
        width=max_width if (max_width is not None and max_width > 0) else None,
        no_color=False,
        log_path=False,
        log_time=False,
        color_system="256",
    )
    logging.basicConfig(
        level="DEBUG" if verbose else "INFO",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(markup=True, console=console, show_path=show_path)],
    )
    return console


def parse_config_from_supplied_location(ctx: click.Context, param) -> dict[str, str]:
    if (
        not ctx.parent
        or ctx.parent.params["config"] is None
        or not Path(ctx.parent.params["config"]).exists()
    ):
        raise BadParameter(
            "Either --config parameter must or MPYL_CONFIG_PATH env var must be set",
            ctx=ctx,
            param=param,
        )
    return parse_config(ctx.parent.params["config"])
