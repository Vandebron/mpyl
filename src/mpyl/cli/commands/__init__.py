"""CLI commands"""
import importlib
from dataclasses import dataclass
from importlib.metadata import version as version_meta

from rich.console import Console

from ...utilities.repo import Repository


@dataclass(frozen=True)
class CliContext:
    config: dict
    repo: Repository
    console: Console
    verbose: bool


def get_version():
    try:
        return f"v{version_meta('mpyl')}"
    except importlib.metadata.PackageNotFoundError:
        return '(local)'


CONFIG_PATH_HELP = 'Path to the config.yml. Needs to comply with schema at ' \
                   'https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml ' \
                   'Can be set via `MPYL_CONFIG_PATH` env var. '
