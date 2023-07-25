import re

from click.testing import CliRunner
from importlib.metadata import version

from src.mpyl.cli import create_console_logger
from src.mpyl import main_group, add_commands
from tests import root_test_path
from tests.test_resources.test_data import assert_roundtrip


class TestCli:
    resource_path = root_test_path / "cli" / "test_resources"
    config_path = root_test_path / "test_resources/mpyl_config.yml"
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

    def test_projects_lint_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", self.config_path, "lint"],
        )
        assert result  # Hard to assert details since it depends on the changes in the current branch

    def test_projects_lint_all_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", self.config_path, "lint", "--all"],
        )
        assert re.match(r"Validated .* projects\. .* valid, .* invalid", result.output)

    def test_show_project_not_found_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", self.config_path, "show", "job"],
        )
        print(result.output)
        assert re.match(r"Project .* not found", result.output)

    def test_show_project_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", self.config_path, "show", "tests/projects/job"],
        )
        assert_roundtrip(self.resource_path / "show_project_text.txt", result.output)

    def test_list_projects_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", self.config_path, "list"],
        )
        assert_roundtrip(self.resource_path / "list_projects_text.txt", result.output)

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

    def test_create_console(self):
        console = create_console_logger(local=False, verbose=True)
        assert console.width is 135
