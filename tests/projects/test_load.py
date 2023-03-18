from src.mpyl.projects.find import load_projects
from tests.test_resources import test_data


class TestProjectLoad:

    def test_load_all_projects(self):
        with test_data.get_repo() as repo:
            projects = load_projects(repo.root_dir(), repo.find_projects())
        assert len(projects) == 3
