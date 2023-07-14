from src.mpyl.cli import create_console_logger
from src.mpyl.cli.commands.projects.formatting import project_to_markdown
from src.mpyl.projects import ProjectWithDependents
from tests import root_test_path
from tests.test_resources.test_data import get_project, assert_roundtrip


class TestProjects:
    test_formatting_resource_path = (
        root_test_path / "reporting" / "formatting" / "test_resources"
    )

    def test_should_render_project_details_to_console(self):
        project = get_project()
        table, maybe_readme = project_to_markdown(ProjectWithDependents(project, {}))

        assert maybe_readme is None

        table_lines = [
            line.text for line in create_console_logger(True, False).render(table)
        ]
        assert_roundtrip(
            self.test_formatting_resource_path / "project_console.txt",
            str("".join(table_lines)),
        )
