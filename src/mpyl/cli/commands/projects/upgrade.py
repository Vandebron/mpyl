"""Upgrade a project configuration file to the latest version."""

from pathlib import Path
from typing import Optional

from deepdiff import DeepDiff
from rich.console import Console

from ....projects.versioning import diff_to_string


def check_upgrade(
    console: Console, all_projects: list[tuple[Path, Optional[DeepDiff]]]
):
    for project_path, diff in all_projects:
        if diff:
            console.print(f"❌ {project_path} {diff_to_string(diff)}")
        else:
            console.print(f"✅ {project_path}")
