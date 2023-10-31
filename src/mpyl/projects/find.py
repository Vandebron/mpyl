""" Loads all projects inside a repository. """
from pathlib import Path
from typing import Optional

from . import ProjectWithDependents, Protocol, Contract, Dependency
from ..project import Project, load_project
from ..steps import test


def load_projects(
    root_dir: Path, paths: list[str], strict: bool = False
) -> set[Project]:
    return set(map(lambda p: load_project(root_dir, Path(p), strict), paths))


def find_by_contract_dep(
    dep: str, projects: list[ProjectWithDependents]
) -> Optional[ProjectWithDependents]:
    for project in projects:
        if project.project.root_path.replace("./", "") in dep:
            return project
    return None


def find_dependencies(
    project: Project, other_projects: set[Project]
) -> ProjectWithDependents:
    mapped = list(map(lambda p: ProjectWithDependents(p, {}), other_projects))

    def recursively_find(
        proj: ProjectWithDependents,
        other: list[ProjectWithDependents],
        discovery_stack: list[str],
    ):
        dependent_projects = {}
        for dep in (
            proj.project.dependencies.set_for_stage(test.STAGE_NAME)
            if proj.project.dependencies
            else set()
        ):
            found = find_by_contract_dep(dep, other)
            if found:
                if found.name not in discovery_stack:
                    discovery_stack.append(found.name)
                    recursively_find(found, other, discovery_stack[:])
                    dependent_projects[found.name] = Dependency(
                        found.project, {Contract(Protocol.UNKNOWN, dep)}
                    )
                elif found.name in dependent_projects:
                    dependent_projects[found.name].contracts.add(
                        Contract(Protocol.UNKNOWN, dep)
                    )

        proj.dependent_projects = dependent_projects
        return proj

    return recursively_find(
        ProjectWithDependents(project=project, dependent_projects={}), mapped, []
    )
