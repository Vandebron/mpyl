""" Loads all projects inside a repository. """
from pathlib import Path
from typing import Optional

from . import ProjectWithDependents, Protocol, Contract, Dependency
from ..project import Project, load_project, Stage


def load_projects(root_dir: Path, paths: list[str]) -> set[Project]:
    return set(map(lambda p: load_project(root_dir, Path(p), False), paths))


def find_by_contract_dep(dep: str, projects: list[ProjectWithDependents]) -> Optional[ProjectWithDependents]:
    for project in projects:
        if project.project.root_path.replace('./', '') in dep:
            return project
    return None


def find_dependencies(project: ProjectWithDependents, all_other: list[ProjectWithDependents],
                      discovery_stack: list[str]):
    dependent_projects = {}
    for dep in project.project.dependencies.set_for_stage(Stage.TEST) if project.project.dependencies else set():
        found_dep = find_by_contract_dep(dep, all_other)
        dep_type = Protocol.UNKNOWN
        if found_dep and found_dep.project.name not in discovery_stack:
            discovery_stack.append(found_dep.project.name)
            find_dependencies(found_dep, all_other, discovery_stack[:])
            dependent_projects[found_dep.project.name] = Dependency(found_dep.project, {Contract(dep_type, dep)})
        elif found_dep and found_dep.project.name in dependent_projects:
            dependent_projects[found_dep.project.name].contracts.add(Contract(dep_type, dep))

    project.dependent_projects = dependent_projects


def find_all_dependencies(root_dir: Path, paths: list[str]) -> list[ProjectWithDependents]:
    projects: list[ProjectWithDependents] = list(
        map(lambda p: ProjectWithDependents(p, {}), load_projects(root_dir, paths)))
    for project in projects:
        find_dependencies(project, projects, [])
    return projects
