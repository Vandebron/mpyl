from pathlib import Path

from tests.test_resources.test_data import assert_roundtrip, root_test_path


class TestDocumentation:
    releases_path = root_test_path / ".." / "releases"

    def test_release_notes(self):
        releases = (
            Path(self.releases_path / "releases.txt")
            .read_text("utf-8")
            .strip()
            .splitlines()
        )
        reverse_chronological = sorted(releases, reverse=True)
        combined = "# Release notes\n\n"
        for release in reverse_chronological:
            combined += f"## MPyL {release}\n\n"

            notes = Path(self.releases_path / "notes" / f"{release}.md")
            if notes.exists():
                combined += "#### Highlights\n\n"
                combined += notes.read_text("utf-8") + "\n\n"
            combined += f"Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/{release})\n\n"

        assert_roundtrip(self.releases_path / "README.md", combined)
