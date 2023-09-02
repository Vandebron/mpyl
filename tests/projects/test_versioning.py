from ruamel.yaml import YAML

from mpyl.projects.versioning import (
    get_next_upgrader,
    upgrade_file,
)
from tests.test_resources.test_data import assert_roundtrip
from tests.test_resources.test_data import root_test_path

yaml = YAML()


class TestVersioning:
    upgrades_path = root_test_path / "test_resources" / "upgrades"

    def test_next_version(self):
        assert get_next_upgrader("1.0.8").target_version == "1.0.9"
        assert get_next_upgrader("1.0.9").target_version == "1.0.10"
        assert get_next_upgrader("1.0.7") is None

    def test_first_upgrade(self):
        assert_roundtrip(
            self.upgrades_path / "test_project_1_0_9.yml",
            upgrade_file(self.upgrades_path / "test_project_1_0_8.yml"),
        )
