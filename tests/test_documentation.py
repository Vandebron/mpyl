from src.mpyl.projects.versioning import (
    render_release_notes,
)
from tests.test_resources.test_data import assert_roundtrip, root_test_path


class TestDocumentation:
    source_root_path = root_test_path / ".."
    releases_path = source_root_path / "releases"
    releases_list_path = source_root_path / "src/mpyl/cli/releases"

    def test_release_notes(self):
        assert_roundtrip(self.releases_path / "README.md", render_release_notes())
