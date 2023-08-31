import re
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

            file = f"{release}.md"
            notes = Path(self.releases_path / "notes" / file)
            if notes.exists():
                combined += "#### Highlights\n\n"
                text = notes.read_text("utf-8")

                # Titles mess up the TOC in the documentation
                assert not re.match("^# ", text), f"{file} contains a title"
                assert not re.match("^## ", text), f"{file} contains a subtitle"
                assert not re.match("^### ", text), f"{file} contains a sub sub title"

                combined += text + "\n\n"
            combined += f"Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/{release})\n\n"

        assert_roundtrip(self.releases_path / "README.md", combined)

    def test_get_latest_release(self):
        assert get_latest_release() == "1.0.11"
