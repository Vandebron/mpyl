from src.mpyl.project import load_project, get_env_variables
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.steps.models import Input
from tests import root_test_path
from tests.test_resources import test_data


class TestEphemeral:
    resource_path = root_test_path / "projects" / "ephemeral" / "deployment"
    config_resource_path = root_test_path / "test_resources"

    def test_get_env_variables_for_target(self):
        step_input = Input(
            ProjectExecution(
                project=load_project(
                    self.config_resource_path, self.resource_path / "project.yml", True
                ),
                changed_files=frozenset(),
                hashed_changes=None,
                cached=False,
            ),
            test_data.RUN_PROPERTIES,
            None,
        )
        deployment = step_input.project_execution.project.deployment
        assert deployment is not None
        assert deployment.properties is not None
        assert len(deployment.properties.env) == 4

        env_variables = get_env_variables(
            step_input.project_execution.project, test_data.RUN_PROPERTIES.target
        )
        assert len(env_variables) == 4
