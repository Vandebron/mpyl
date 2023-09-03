from ruamel.yaml import YAML

from mpyl.projects.versioning import (
    upgrade_file,
    UPGRADERS,
    Upgrader10,
    Upgrader9,
    Upgrader8,
    get_entry_upgrader_index,
)
from tests.test_resources.test_data import assert_roundtrip
from tests.test_resources.test_data import root_test_path

yaml = YAML()


class TestVersioning:
    upgrades_path = root_test_path / "test_resources" / "upgrades"

    def test_get_upgrader_index(self):
        assert get_entry_upgrader_index("1.0.8", UPGRADERS) == 0
        assert get_entry_upgrader_index("1.0.9", UPGRADERS) == 1
        assert get_entry_upgrader_index("1.0.7", UPGRADERS) is None

    def test_first_upgrade(self):
        assert_roundtrip(
            self.upgrades_path / "test_project_1_0_9.yml",
            upgrade_file(
                self.upgrades_path / "test_project_1_0_8.yml",
                [Upgrader8(), Upgrader9()],
            ),
        )

    def test_namespace_upgrade(self):
        assert_roundtrip(
            self.upgrades_path / "test_project_1_0_10.yml",
            upgrade_file(
                self.upgrades_path / "test_project_1_0_9.yml",
                [Upgrader9(), Upgrader10()],
            ),
        )

    def test_full_upgrade(self):
        assert_roundtrip(
            self.upgrades_path / "test_project_1_0_11.yml",
            upgrade_file(self.upgrades_path / "test_project_1_0_8.yml", UPGRADERS),
        )
