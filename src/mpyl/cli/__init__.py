"""Command Line Interface parsing for MPyL"""
import importlib
import logging
from dataclasses import dataclass
from importlib.metadata import version as version_meta

import requests
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


def get_version():
    try:
        meta = version_meta('mpyl')
        try:
            resp = requests.get("https://pypi.org/pypi/mpyl/json", timeout=3)
            latest = resp.json().get('info', {}).get('version')
            if meta != latest:
                return f"v{meta}. ⚠️ \033[1;33;40m A newer version is available: `pip install -U {latest}`"
        except requests.exceptions.RequestException:
            pass
        return f"v{meta}"
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
