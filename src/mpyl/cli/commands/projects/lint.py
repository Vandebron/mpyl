"""Helper methods for linting projects for correctnessare can be found here"""

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
    valid = [project for project in projects if project]
    invalid = len(projects) - len(valid)
    if console:
        console.print(
            f"Validated {len(valid) + invalid} projects. {len(valid)} valid, {invalid} invalid"
        )
    if invalid > 0:
        click.get_current_context().exit(1)
    return valid


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
    console.print("✅ No duplicate project names found")


def __get_project_name(project: Project) -> ProjectName:
    namespace = project.deployment.namespace if project.deployment else None
    return ProjectName(project.name, namespace)


def _assert_correct_project_linkup(
    console: Console,
    target: Target,
    projects: list[Project],
    all_projects: list[Project],
    pr_identifier: Optional[int],
):
    wrong_substitutions_per_project = __get_wrong_substitutions_per_project(
        all_projects, projects, pr_identifier, target
    )
    if len(wrong_substitutions_per_project.keys()) == 0:
        console.print("✅ No wrong namespace substitutions found")
    else:
        __detail_wrong_substitutions(
            console, all_projects, wrong_substitutions_per_project
        )


def __get_wrong_substitutions_per_project(
    all_projects: list[Project],
    projects: list[Project],
    pr_identifier: Optional[int],
    target: Target,
):
    wrong_substitutions_per_project: dict[str, list[tuple[str, str]]] = {}
    for project in projects:
        if project.deployment:
            substituted: dict[str, str] = substitute_namespaces(
                env_vars=ChartBuilder.extract_raw_env(
                    target=target, env=project.deployment.properties.env
                ),
                all_projects=set(map(__get_project_name, all_projects)),
                projects_to_deploy=set(map(__get_project_name, projects)),
                pr_identifier=pr_identifier,
            )
            wrong_subs = [(k, v) for k, v in substituted.items() if "{namespace}" in v]
            if len(wrong_subs) > 0:
                wrong_substitutions_per_project[project.name] = wrong_subs
    return wrong_substitutions_per_project


def __detail_wrong_substitutions(
    console: Console,
    all_projects: list[Project],
    wrong_substitutions_per_project: dict[str, list[tuple[str, str]]],
):
    all_project_names: dict[str, str] = {
        project.name.lower(): project.name for project in all_projects
    }
    for project_name, wrong_subsitutions in wrong_substitutions_per_project.items():
        console.print(f"❌ Project {project_name} has wrong namespace substitutions:")
        for env, url in wrong_subsitutions:
            unrecognized_project_name = url.split(".{namespace}")[0].split("/")[-1]
            suggestion = all_project_names.get(unrecognized_project_name.lower())
            console.print(
                f"  {env} references unrecognized project {unrecognized_project_name}"
                + (f" (did you mean {suggestion}?)" if suggestion else "")
            )
