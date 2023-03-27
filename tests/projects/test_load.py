from src.mpyl.projects import ProjectWithDependents
from src.mpyl.projects.find import load_projects, find_all_dependencies
from tests.test_resources import test_data


class TestProjectLoad:

    def test_load_all_projects(self):
        with test_data.get_repo() as repo:
            projects = load_projects(repo.root_dir(), repo.find_projects())
        assert len(projects) == 4

    def test_load_all_project_dependencies(self):
        with test_data.get_repo() as repo:
            dependencies = find_all_dependencies(repo.root_dir(), repo.find_projects())
            deps: dict[str, ProjectWithDependents] = dict(map(lambda d: (d.name, d), dependencies))

        assert len(dependencies) == 4
        assert len(deps['job'].dependent_projects) == 1
        assert len(deps['sbtservice'].dependent_projects) == 0
