"""CLI commands"""
from dataclasses import dataclass

from rich.console import Console

from ...utilities.repo import Repository


@dataclass(frozen=True)
class CliContext:
    config: dict
    repo: Repository
    console: Console
