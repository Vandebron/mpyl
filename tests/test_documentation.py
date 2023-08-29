from pathlib import Path

from src.mpyl.cli import get_releases, get_latest_release
from tests.test_resources.test_data import assert_roundtrip, root_test_path


class TestDocumentation:
    source_root_path = root_test_path / ".."
    releases_path = source_root_path / "releases"
    releases_list_path = source_root_path / "src/mpyl/cli/releases"

    def test_release_notes(self):
        reverse_chronological = get_releases()
        combined = "# Release notes\n\n"
        for release in reverse_chronological:
            combined += f"## MPyL {release}\n\n"

            notes = Path(self.releases_path / "notes" / f"{release}.md")
            if notes.exists():
                combined += "#### Highlights\n\n"
                combined += notes.read_text("utf-8") + "\n\n"
            combined += f"Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/{release})\n\n"

        assert_roundtrip(self.releases_path / "README.md", combined)

    def test_get_latest_release(self):
        assert get_latest_release() == "1.0.11"
