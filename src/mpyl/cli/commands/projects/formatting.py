"""Serialization of projects for display purposes"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ... import Repository
from ....project import load_project
from ....projects.find import load_projects, find_dependencies


def print_project(repo: Repository, console: Console, project_path: str):
    project = load_project(repo.root_dir(), Path(project_path), False)
    other_projects = load_projects(repo.root_dir(), repo.find_projects())

    with_dependencies = find_dependencies(project, other_projects)

    table = Table(title=f"Project {project.name}", show_header=False)
    table.add_row("Name", project.name)
    table.add_row("Path", project.path)
    table.add_row("Description", project.description)
    table.add_row("Maintainer", f"{project.maintainer}")
    table.add_row("Stages", f"{project.stages}")
    if with_dependencies.dependent_projects:
        table.add_row("Dependent projects", f"{set(with_dependencies.dependent_projects.keys())}")
    console.print(table)
