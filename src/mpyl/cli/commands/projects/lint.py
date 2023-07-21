from pathlib import Path
from typing import Optional

import click
import jsonschema
from rich.console import Console

from ....steps.deploy.k8s import substitute_namespaces
from ....steps.deploy.k8s.chart import ChartBuilder
from ....utilities.repo import Repository
from ....cli.commands.build.mpyl import find_build_set
from ....project import Project, load_project, ProjectName, Target


def _find_projects(all_: bool, repo: Repository, filter_: str):
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
    console: Optional[Console],
    root_dir: Path,
    project_path: str,
    verbose: bool = False,
    strict: bool = True,
) -> Optional[Project]:
    try:
        project = load_project(root_dir, Path(project_path), strict)
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
    console: Optional[Console], repo: Repository, project_paths: list[str], strict: bool
) -> list[Project]:
    projects = [
        __load_project(console, repo.root_dir(), project_path, strict)
        for project_path in set(project_paths)
    ]
    valid = len([project for project in projects if project])
    invalid = len(projects) - valid
    if console:
        console.print(
            f"Validated {valid + invalid} projects. {valid} valid, {invalid} invalid"
        )
    if invalid > 0:
        click.get_current_context().exit(1)
    return projects


def _assert_unique_project_names(
    console: Console, projects: list[Project], all_projects: list[Project]
):
    current_project_names: set[str] = {project.name for project in projects}
    remaining_project_names: set[str] = {
        project.name for project in set(all_projects)
    }.difference(current_project_names)
    duplicates = current_project_names.intersection(remaining_project_names)
    if duplicates:
        console.print(
            f"❌ Found {len(duplicates)} duplicate project names: {duplicates}"
        )
        click.get_current_context().exit(1)
    console.print(f"✅ No duplicate project names found")


def __get_project_name(project: Project) -> ProjectName:
    namespace = project.deployment.namespace if project.deployment else None
    return ProjectName(project.name, namespace)


def _assert_correct_project_linkup(
    console: Console,
    target: Target,
    projects: list[Project],
    all_projects: list[Project],
    pr_identifier: Optional[str],
):
    project_names = set(map(__get_project_name, projects))
    all_project_names = set(map(__get_project_name, all_projects))

    for project in projects:
        console.print(f"Checking namespace substitution for project {project.name}")
        env_vars = ChartBuilder.extract_raw_env(
            target=target, env=project.deployment.properties.env
        )
        substituted: dict[str, str] = substitute_namespaces(
            env_vars=env_vars,
            all_projects=all_project_names,
            projects_to_deploy=project_names,
            pr_identifier=pr_identifier,
        )
        wrong_subst = [k for k, v in substituted.items() if "{namespace}" in v]
        if len(wrong_subst) == 0:
            console.print(f"✅ No wrong namespace substitutions found")
        else:
            console.print(
                f"❌ Found {len(wrong_subst)} wrong namespace substitutions: {wrong_subst}"
            )
