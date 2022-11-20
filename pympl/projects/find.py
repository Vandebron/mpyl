from pympl.project import Project, load_project


def load_projects(root_dir: str, paths: set[str]) -> list[Project]:
    return list(map(lambda p: load_project(f'{root_dir}/{p}', False), paths))
