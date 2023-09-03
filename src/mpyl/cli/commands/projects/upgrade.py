"""Upgrade a project configuration file to the latest version."""

from pathlib import Path

from rich.console import Console

from ....projects.versioning import check_upgrade_needed, diff_to_string


def check_upgrade(console: Console, all_projects: list[Path]):
    for project_path in all_projects:
        diff = check_upgrade_needed(project_path)
        if diff:
            console.print(f"❌ {project_path} {diff_to_string(diff)}")
        else:
            console.print(f"✅ {project_path}")
