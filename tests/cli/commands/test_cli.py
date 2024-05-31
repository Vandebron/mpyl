import platform
import re

import pytest
from click.testing import CliRunner

from src.mpyl import main_group, add_commands
from src.mpyl.cli import create_console_logger
from tests import root_test_path
from tests.test_resources.test_data import assert_roundtrip


class TestCli:
    resource_path = root_test_path / "cli" / "test_resources"
    config_path = root_test_path / "test_resources/mpyl_config.yml"
    run_properties_path = root_test_path / "test_resources/run_properties.yml"
    runner = CliRunner()
    add_commands()

    def test_cli_help_output(self):
        result = self.runner.invoke(main_group, ["--help"])
        assert_roundtrip(self.resource_path / "main_help_text.txt", result.output)

    def test_build_projects_help_output(self):
        result = self.runner.invoke(main_group, ["build", "--help"])
        assert_roundtrip(self.resource_path / "build_help_text.txt", result.output)

    def test_projects_help_output(self):
        result = self.runner.invoke(main_group, ["projects", "--help"])
        assert_roundtrip(self.resource_path / "projects_help_text.txt", result.output)

    def test_projects_lint_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", str(self.config_path), "lint"],
        )
        assert result  # Hard to assert details since it depends on the changes in the current branch

    def test_projects_lint_all_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", str(self.config_path), "lint"],
        )
        assert re.match(
            r"(.|\n)*Validated .* projects\. .* valid, .* invalid\n\nChecking for duplicate project names: \n.*No duplicate project names found",
            result.output,
        )

    def test_show_project_not_found_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", str(self.config_path), "show", "job"],
        )
        assert re.match(r"Project .* not found", result.output)

    def test_show_project_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", str(self.config_path), "show", "tests/projects/job"],
        )
        assert_roundtrip(self.resource_path / "show_project_text.txt", result.output)

    def test_list_projects_output(self):
        result = self.runner.invoke(
            main_group,
            ["projects", "-c", str(self.config_path), "list"],
        )
        assert_roundtrip(self.resource_path / "list_projects_text.txt", result.output)

    def test_version_print(self):
        result = self.runner.invoke(
            main_group,
            ["version"],
        )

        if platform.system() == "Darwin":
            regex = r"MPyL \d+\.\d+\.\d+"
        else:
            regex = r"MPyL \(local\)"

        assert re.match(regex, result.output)

    @pytest.mark.skipif(
        condition=platform.system() != "Darwin",
        reason="mpyl distribution is not available in github action",
    )
    def test_verbose_version_print(self):
        result = self.runner.invoke(
            main_group,
            ["version", "-v"],
        )
        assert_roundtrip(
            self.resource_path / "metadata_text.txt",
            re.sub(r"Version: .*", "Version: {version}", result.output, re.M),
        )
