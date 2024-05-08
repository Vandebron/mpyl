from src.mpyl.utilities.repo import RepoConfig, Changeset
from tests import root_test_path
from tests.test_resources.test_data import get_config_values


class TestRepo:
    resource_path = root_test_path / "test_resources" / "repository"

    def test_load_config(self):
        config = RepoConfig.from_config(get_config_values())
        assert config.main_branch == "main"
        repo_credentials = config.repo_credentials
        assert repo_credentials.url == "https://github.com/acme/repo.git"
        assert (
            repo_credentials.to_url_with_credentials
            == "https://git-user:git-password@github.com/acme/repo.git"
        )

    def test_from_diff(self):
        sha = "a sha"
        diff_text = set(
            (self.resource_path / "git_diff_name_status.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        changeset = Changeset.from_diff(sha, diff_text)

        assert changeset.sha == "a sha"
        assert changeset.files_touched() == {
            "projects/a/this-file-was-added",
            "projects/b/this-file-was-renamed",
            "projects/c/this-file-was-removed",
        }

    def test_from_diff_with_filter(self):
        sha = "a sha"
        diff_text = set(
            (self.resource_path / "git_diff_name_status.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        changeset = Changeset.from_diff(sha, diff_text)

        assert changeset.sha == "a sha"
        assert changeset.files_touched(status={"A", "R"}) == {
            "projects/a/this-file-was-added",
            "projects/b/this-file-was-renamed",
        }
