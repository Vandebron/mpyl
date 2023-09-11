"""Upgrade a project configuration file to the latest version."""

from pathlib import Path
from typing import Optional, Generator

from deepdiff import DeepDiff
from rich.console import Console

from ....projects.versioning import pretty_print


def check_upgrade(
    console: Console,
    all_projects: Generator[tuple[Path, Optional[DeepDiff]], None, None],
) -> list[Path]:
    to_upgrade = []
    for project_path, diff in all_projects:
        if diff:
            console.print(f"❌ {project_path} {pretty_print(diff)}")
            to_upgrade.append(project_path)
        else:
            console.print(f"✅ {project_path}")
    return to_upgrade
