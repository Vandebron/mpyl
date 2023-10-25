from src.mpyl.projects import ProjectWithDependents
from src.mpyl.projects.find import load_projects, find_dependencies
from tests.test_resources import test_data


class TestProjectLoad:
    def test_load_all_projects(self):
        with test_data.get_repo() as repo:
            projects = load_projects(repo.root_dir, repo.find_projects(), True)
            assert len(projects) == 11

    def test_load_all_project_dependencies(self):
        with test_data.get_repo() as repo:
            projects = load_projects(repo.root_dir, repo.find_projects())
            dependencies = list(map(lambda p: find_dependencies(p, projects), projects))
            deps: dict[str, ProjectWithDependents] = dict(
                map(lambda d: (d.name, d), dependencies)
            )

            assert len(dependencies) == 11
            assert len(deps["job"].dependent_projects) == 1
            assert len(deps["sbtservice"].dependent_projects) == 0
