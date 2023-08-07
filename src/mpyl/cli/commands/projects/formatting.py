"""Serialization of projects for display purposes"""

from pathlib import Path
from typing import Tuple, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ... import Repository
from ....project import load_project
from ....projects import ProjectWithDependents
from ....projects.find import load_projects, find_dependencies


def print_project(repo: Repository, console: Console, project_path: str):
    project = load_project(repo.root_dir, Path(project_path), False)
    other_projects = load_projects(repo.root_dir, repo.find_projects())

    with_dependencies = find_dependencies(project, other_projects)

    table, readme = project_to_markdown(with_dependencies)
    console.print(table, readme)


def project_to_markdown(
    with_dependencies: ProjectWithDependents,
) -> Tuple[Table, Optional[Markdown]]:
    project = with_dependencies.project
    table = Table(title=f"Project {project.name}", show_header=False)
    table.add_row("Name", project.name)
    table.add_row("Path", project.path)
    table.add_row("Description", project.description)
    table.add_row("Maintainer", f"{project.maintainer}")
    table.add_row("Stages", f"{project.stages}")
    if with_dependencies.dependent_projects:
        table.add_row(
            "Dependent projects", f"{set(with_dependencies.dependent_projects.keys())}"
        )
    readme = Path(project.root_path, "README.md")
    return (
        table,
        Markdown(readme.read_text(encoding="utf-8")) if readme.exists() else None,
    )
