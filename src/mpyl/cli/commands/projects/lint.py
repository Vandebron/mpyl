from pathlib import Path
from typing import Optional

import click
import jsonschema
from rich.console import Console

from ....utilities.repo import Repository
from ....cli.commands.build.mpyl import find_build_set
from ....project import Project, load_project


def _find_projects(all_, repo: Repository, filter_: str):
    project_paths = []
    if all_:
        project_paths = repo.find_projects(filter_)
    else:
        branch = repo.get_branch
        changes = (
            repo.changes_in_branch_including_local()
            if branch
            else repo.changes_in_merge_commit()
        )
        build_set = find_build_set(repo, changes, False)
        for all_projects in build_set.values():
            for project in all_projects:
                project_paths.append(project.path)
    return project_paths


def __load_project(
    console: Optional[Console], root_dir: Path, project_path: str, verbose: bool = False
) -> Optional[Project]:
    try:
        project = load_project(root_dir, Path(project_path), strict=True)
    except jsonschema.exceptions.ValidationError as exc:
        if console:
            console.print(f"❌ {project_path}: {exc.message}")
        return None
    except Exception as exc:  # pylint: disable=broad-except
        if console:
            console.print(f"❌ {project_path}: {exc}")
        return None
    else:
        if console and verbose:
            console.print(f"✅ {project_path}")
        return project


def _check_and_load_projects(
    console: Console, repo: Repository, project_paths: list[str]
) -> list[Project]:
    projects = [
        __load_project(console, repo.root_dir(), project_path)
        for project_path in set(project_paths)
    ]
    valid = len([project for project in projects if project])
    invalid = len(projects) - valid
    console.print(
        f"Validated {valid + invalid} projects. {valid} valid, {invalid} invalid"
    )
    if invalid > 0:
        click.get_current_context().exit(1)
    return projects


def _assert_unique_project_names(
    console: Console, repo: Repository, projects: list[Project]
):
    current_project_names: set[str] = {project.name for project in projects}
    remaining_project_names: set[str] = {
        __load_project(None, repo.root_dir(), project_path).name
        for project_path in repo.find_projects()
    }.difference(current_project_names)
    duplicates = current_project_names.intersection(remaining_project_names)
    if duplicates:
        console.print(
            f"❌ Found {len(duplicates)} duplicate project names: {duplicates}"
        )
        click.get_current_context().exit(1)
    console.print(f"✅ No duplicate project names found")
