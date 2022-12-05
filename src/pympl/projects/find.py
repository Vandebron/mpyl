from ..project import Project, load_project


def load_projects(root_dir: str, paths: set[str]) -> set[Project]:
    return set(map(lambda p: load_project(root_dir, p, False), paths))
