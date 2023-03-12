""" Loads all projects inside a repository. """
from pathlib import Path

from ..project import Project, load_project


def load_projects(root_dir: Path, paths: set[str]) -> set[Project]:
    return set(map(lambda p: load_project(root_dir, Path(p), False), paths))
