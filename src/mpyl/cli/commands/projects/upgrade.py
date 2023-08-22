"""Helper methods for upgrading project definitions to the latest version"""
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


def upgrade_project(console: Console, project_path: Path):
    console.print(Markdown(f"Upgrading `{project_path}`"))
