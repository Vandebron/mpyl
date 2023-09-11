"""Helper methods for linting projects for correctnessare can be found here"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
import jsonschema
from rich.console import Console

from ....steps.deploy.k8s import substitute_namespaces
from ....steps.deploy.k8s.chart import ChartBuilder
from ....utilities.repo import Repository
from ....build import find_build_set
from ....project import Project, load_project, Target


def _find_project_paths(all_: bool, repo: Repository, filter_: str):
    project_paths: list[str] = []
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
    if console and verbose:
        console.print(f"✅ {project_path}")
    return project


def _check_and_load_projects(
    console: Optional[Console], repo: Repository, project_paths: list[str], strict: bool
) -> list[Project]:
    projects = [
        __load_project(console, repo.root_dir, project_path, strict)
        for project_path in set(project_paths)
    ]
    valid_projects = [project for project in projects if project]
    num_invalid = len(projects) - len(valid_projects)
    if console:
        console.print(
            f"Validated {len(projects)} projects. {len(valid_projects)} valid, {num_invalid} invalid"
        )
    if num_invalid > 0 and strict:
        click.get_current_context().exit(1)
    return valid_projects


def _assert_unique_project_names(console: Console, all_projects: list[Project]):
    console.print("")
    duplicates = [
        project.name for project in all_projects if all_projects.count(project) > 1
    ]
    if duplicates:
        console.print(
            f"❌ Found {len(duplicates)} duplicate project names: {duplicates}"
        )
        click.get_current_context().exit(1)
    console.print("✅ No duplicate project names found")


@dataclass
class WrongLinkupPerProject:
    name: str
    wrong_substitutions: list[tuple[str, str]]


def _assert_correct_project_linkup(
    console: Console,
    target: Target,
    projects: list[Project],
    all_projects: list[Project],
    pr_identifier: Optional[int],
):
    console.print("")
    wrong_substitutions = __get_wrong_substitutions_per_project(
        all_projects, projects, pr_identifier, target
    )
    if len(wrong_substitutions) == 0:
        console.print("✅ No wrong namespace substitutions found")
    else:
        __detail_wrong_substitutions(console, all_projects, wrong_substitutions)


def __get_wrong_substitutions_per_project(
    all_projects: list[Project],
    projects: list[Project],
    pr_identifier: Optional[int],
    target: Target,
) -> list[WrongLinkupPerProject]:
    project_linkup: list[WrongLinkupPerProject] = []
    for project in projects:
        if project.deployment and project.deployment.properties:
            env = ChartBuilder.extract_raw_env(
                target=target, env=project.deployment.properties.env
            )
            substituted: dict[str, str] = substitute_namespaces(
                env_vars=env,
                all_projects=set(map(lambda p: p.to_name, all_projects)),
                projects_to_deploy=set(map(lambda p: p.to_name, projects)),
                pr_identifier=pr_identifier,
            )
            wrong_subs = list(
                filter(lambda x: "{namespace}" in x[1], substituted.items())
            )
            if len(wrong_subs) > 0:
                project_linkup.append(WrongLinkupPerProject(project.name, wrong_subs))
    return project_linkup


def __detail_wrong_substitutions(
    console: Console,
    all_projects: list[Project],
    wrong_substitutions_per_project: list[WrongLinkupPerProject],
):
    all_project_names: dict[str, str] = {
        project.name.lower(): project.name for project in all_projects
    }
    for project in wrong_substitutions_per_project:
        console.print(f"❌ Project {project.name} has wrong namespace substitutions:")
        for env, url in project.wrong_substitutions:
            unrecognized_project_name = url.split(".{namespace}")[0].split("/")[-1]
            suggestion = all_project_names.get(unrecognized_project_name.lower())
            console.print(
                f"  {env} references unrecognized project {unrecognized_project_name}"
                + (f" (did you mean {suggestion}?)" if suggestion else "")
            )
