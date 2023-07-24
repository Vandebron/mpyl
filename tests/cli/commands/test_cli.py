import re

from click.testing import CliRunner
from importlib.metadata import version

from src.mpyl import main_group, add_commands
from tests import root_test_path
from tests.test_resources.test_data import assert_roundtrip


class TestCli:
    resource_path = root_test_path / "cli" / "test_resources"
    runner = CliRunner()
    add_commands()

    def test_cli_help_output(self):
        result = self.runner.invoke(main_group, ["--help"])
        assert_roundtrip(self.resource_path / "main_help_text.txt", result.output)

    def test_cli_projects_help_output(self):
        result = self.runner.invoke(main_group, ["projects", "--help"])
        assert_roundtrip(self.resource_path / "projects_help_text.txt", result.output)

    def test_build_projects_help_output(self):
        result = self.runner.invoke(main_group, ["build", "--help"])
        assert_roundtrip(self.resource_path / "build_help_text.txt", result.output)

    def test_lint_output(self):
        config_path = root_test_path / "test_resources/mpyl_config.yml"
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", config_path, "lint", "--all"],
        )
        assert re.match(r"Validated .* projects\. .* valid, .* invalid", result.output)

    def test_version_print(self):
        result = self.runner.invoke(
            main_group,
            ["version"],
        )
        assert re.match(r"MPyL v\d+\.\d+\.\d+", result.output)

    def test_verbose_version_print(self):
        result = self.runner.invoke(
            main_group,
            ["version", "-v"],
        )

        with open(self.resource_path / "metadata_text.txt", encoding="utf-8") as file:
            expected = file.read().replace("{version}", version("mpyl"))
            assert result.output == expected
