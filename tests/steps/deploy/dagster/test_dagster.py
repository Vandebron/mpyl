import tempfile
from pathlib import Path

import yaml

from mpyl import parse_config
from mpyl.project import load_project
from mpyl.steps import Input
from mpyl.steps.deploy.k8s.resources.dagster import to_user_code_values
from mpyl.utilities.docker import DockerConfig
from tests import root_test_path
from tests.test_resources import test_data


class TestDagster:
    resource_path = root_test_path / "projects" / "dagster-user-code" / "deployment"
    generated_values_path = (
        root_test_path / "steps" / "deploy" / "dagster" / "dagster-user-deployments"
    )
    config_resource_path = root_test_path / "test_resources"

    def test_generate_correct_dagster_config(self):
        step_input = Input(
            load_project(self.resource_path, Path("project.yml"), True),
            test_data.RUN_PROPERTIES,
            None,
        )

        assert step_input.project.dagster.repo == "/example/repo.py"
        assert len(step_input.project.dagster.secrets) == 2

    def test_generate_correct_values_yaml(self):
        step_input = Input(
            load_project(self.resource_path, Path("project.yml"), True),
            test_data.RUN_PROPERTIES,
            None,
        )

        with open(
            self.generated_values_path / "values.yaml", "r"
        ) as expected_values_file:
            expected_values = yaml.safe_load(expected_values_file)
            values = to_user_code_values(
                project=step_input.project,
                name_suffix="-pr-1234",
                run_properties=test_data.RUN_PROPERTIES,
                docker_config=DockerConfig.from_dict(
                    parse_config(Path(f"{self.config_resource_path}/mpyl_config.yml"))
                ),
            )

            assert values == expected_values
