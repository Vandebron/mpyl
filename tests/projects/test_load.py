import traceback
from pathlib import Path

import jsonschema

from src.mpyl.project import load_project
from src.mpyl.projects import ProjectWithDependents
from tests.projects.find import load_projects, find_dependencies
from tests.test_resources import test_data


class TestProjectLoad:
    def test_load_all_projects(self):
        with test_data.get_repo() as repo:
            for project in repo.find_projects():
                try:
                    load_project(repo.root_dir, Path(project), True)
                except jsonschema.exceptions.ValidationError as exc:
                    traceback.print_exc()
                    assert exc == project

    def test_load_all_project_dependencies(self):
        with test_data.get_repo() as repo:
            projects = load_projects(repo.root_dir, repo.find_projects())
            dependencies = list(map(lambda p: find_dependencies(p, projects), projects))
            deps: dict[str, ProjectWithDependents] = dict(
                map(lambda d: (d.name, d), dependencies)
            )

            assert len(dependencies) == 7
            assert len(deps["job"].dependent_projects) == 1
            assert len(deps["sbtservice"].dependent_projects) == 0
