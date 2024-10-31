from rich.console import Console
from rich.markdown import Markdown

from src.mpyl.cli.commands.health.checks import _validate_config, HealthConsole
from tests import root_test_path


class TestConsole(Console):
    def __init__(self):
        self._stdout = []

    def print(self, something: Markdown):  # type: ignore
        self._stdout.append(str(something.markup))

    def output(self):
        return "\n".join(self._stdout)


class TestHealthCommand:
    resource_path = root_test_path / "test_resources" / "dynamic_stages"

    def test_validate_run_properties(self):
        test_console = TestConsole()

        _validate_config(
            HealthConsole(test_console),
            self.resource_path / "run_properties.yml",
            "../../../schema/run_properties.schema.yml",
            root_dir=self.resource_path,
        )

        assert "is valid" in test_console.output()

    def test_validate_run_properties_two(self):
        test_console = TestConsole()
        _validate_config(
            HealthConsole(test_console),
            self.resource_path / "run_properties_incorrect_stage_name.yml",
            "../../../schema/run_properties.schema.yml",
            root_dir=self.resource_path,
        )

        assert (
            "'invalidStage' is not one of ['firstStage', 'secondStage']"
            in test_console.output()
        )
