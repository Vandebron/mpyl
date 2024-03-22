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
        diff_text = (
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
        diff_text = (
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

    def test_map_git_log_to_revisions(self):
        log_text = (self.resource_path / "git_log.txt").read_text(encoding="utf-8")
        diff_text = (self.resource_path / "git_diff.txt").read_text(encoding="utf-8")
        revisions = Changeset.from_git_output(log_text, diff_text)

        first_revision = revisions[0]
        assert first_revision.sha == "e9ff18931070de4803da2190274d5fccb0362824"
        assert first_revision.files_touched() == {"projects/service/src/sum.js"}

        last_revision = revisions[-1]
        assert (
            last_revision.files_touched() == set()
        ), "Pipfile does not have a net change"
