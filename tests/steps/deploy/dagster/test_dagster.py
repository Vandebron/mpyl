from pathlib import Path

from ruamel.yaml import YAML

from src.mpyl import parse_config
from src.mpyl.project import load_project
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.steps import Input
from src.mpyl.steps.deploy.k8s.chart import ChartBuilder
from src.mpyl.steps.deploy.k8s.resources.dagster import to_user_code_values
from src.mpyl.utilities.docker import DockerConfig
from src.mpyl.utilities.helm import get_name_suffix
from src.mpyl.utilities.yaml import yaml_to_string
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip

yaml = YAML()


class TestDagster:
    dagster_project_folder = Path("projects", "dagster-user-code", "deployment")
    resource_path = root_test_path / dagster_project_folder
    generated_values_path = (
        root_test_path / "steps" / "deploy" / "dagster" / "dagster-user-deployments"
    )
    config_resource_path = root_test_path / "test_resources"

    @staticmethod
    def _roundtrip(
        file_name: Path,
        chart: str,
        actual_values: dict,
        overwrite: bool = False,
    ):
        name_chart = file_name / f"{chart}.yaml"
        assert_roundtrip(name_chart, yaml_to_string(actual_values, yaml), overwrite)

    def test_generate_correct_values_yaml_with_service_account_override(self):
        step_input = Input(
            ProjectExecution(
                project=load_project(
                    test_resource_path, self.resource_path / "project.yml", True
                ),
                hashed_changes=None,
                cached=False,
            ),
            test_data.RUN_PROPERTIES,
            None,
        )

        values = to_user_code_values(
            builder=ChartBuilder(step_input),
            release_name="example-dagster-user-code-pr-1234",
            name_suffix=get_name_suffix(test_data.RUN_PROPERTIES),
            run_properties=test_data.RUN_PROPERTIES,
            service_account_override="global_service_account",
            docker_config=DockerConfig.from_dict(
                parse_config(Path(f"{self.config_resource_path}/mpyl_config.yml"))
            ),
        )

        self._roundtrip(
            self.generated_values_path, "values_with_global_service_account", values
        )

    def test_generate_correct_values_yaml_with_production_target(self):
        step_input = Input(
            ProjectExecution(
                project=load_project(
                    test_resource_path, Path(self.resource_path, "project.yml"), True
                ),
                hashed_changes=None,
                cached=False,
            ),
            test_data.RUN_PROPERTIES_PROD,
            None,
        )

        values = to_user_code_values(
            builder=ChartBuilder(step_input),
            release_name="example-dagster-user-code",
            name_suffix=get_name_suffix(test_data.RUN_PROPERTIES_PROD),
            run_properties=test_data.RUN_PROPERTIES_PROD,
            service_account_override="global_service_account",
            docker_config=DockerConfig.from_dict(
                parse_config(Path(f"{self.config_resource_path}/mpyl_config.yml"))
            ),
        )

        self._roundtrip(self.generated_values_path, "values_with_target_prod", values)

    def test_generate_correct_values_yaml_without_service_account_override(self):
        step_input = Input(
            ProjectExecution(
                project=load_project(
                    test_resource_path, Path(self.resource_path, "project.yml"), True
                ),
                hashed_changes=None,
                cached=False,
            ),
            test_data.RUN_PROPERTIES,
            None,
        )

        values = to_user_code_values(
            builder=ChartBuilder(step_input),
            release_name="example-dagster-user-code-pr-1234",
            name_suffix=get_name_suffix(test_data.RUN_PROPERTIES),
            run_properties=test_data.RUN_PROPERTIES,
            service_account_override=None,
            docker_config=DockerConfig.from_dict(
                parse_config(Path(f"{self.config_resource_path}/mpyl_config.yml"))
            ),
        )

        self._roundtrip(
            self.generated_values_path, "values_without_global_service_account", values
        )

    def test_generate_with_sealed_secret_as_extra_manifest(self):
        project_folder = self.config_resource_path / ".." / self.dagster_project_folder
        step_input = Input(
            ProjectExecution(
                project=load_project(
                    self.config_resource_path,
                    project_folder / "project_with_sealed_secret.yml",
                    True,
                ),
                hashed_changes=None,
                cached=False,
            ),
            test_data.RUN_PROPERTIES,
            None,
        )

        values = to_user_code_values(
            builder=ChartBuilder(step_input),
            release_name="example-dagster-user-code-pr-1234",
            name_suffix=get_name_suffix(test_data.RUN_PROPERTIES),
            run_properties=test_data.RUN_PROPERTIES,
            service_account_override=None,
            docker_config=DockerConfig.from_dict(
                parse_config(Path(f"{self.config_resource_path}/mpyl_config.yml"))
            ),
        )

        self._roundtrip(
            self.generated_values_path, "values_with_extra_manifest", values
        )
