""" This is a Python function load_projects that takes two parameters:
root_dir: a string that represents the root directory of the projects.
paths: a set of strings representing the paths of projects to be loaded.
The function returns a set of Project objects.
"""

from ..project import Project, load_project


def load_projects(root_dir: str, paths: set[str]) -> set[Project]:
    return set(map(lambda p: load_project(root_dir, p, False), paths))
