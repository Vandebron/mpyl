import dataclasses
import os
from pathlib import Path

from attr import dataclass
from git import Repo

from src.mpyl.constants import (
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_RUN_PROPERTIES_FILE_NAME,
)
from src.mpyl.project import load_project, Target, Project, Stages, Stage
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.run_plan import RunPlan
from src.mpyl.steps.models import (
    RunProperties,
    Output,
    ArtifactType,
    Artifact,
)
from src.mpyl.steps.run_properties import construct_run_properties
from src.mpyl.utilities.docker import DockerImageSpec
from src.mpyl.utilities.pyaml_env import parse_config
from src.mpyl.utilities.repo import Repository, RepoConfig
from tests import root_test_path

resource_path = root_test_path / "test_resources"
config_values = parse_config(resource_path / DEFAULT_CONFIG_FILE_NAME)
properties_values = parse_config(resource_path / DEFAULT_RUN_PROPERTIES_FILE_NAME)

RUN_PROPERTIES = construct_run_properties(
    config=config_values,
    properties=properties_values,
    run_plan=RunPlan.empty(),
    all_projects=set(),
    root_dir=resource_path,
)

RUN_PROPERTIES_PROD = dataclasses.replace(
    RUN_PROPERTIES,
    target=Target.PRODUCTION,
    versioning=dataclasses.replace(
        RUN_PROPERTIES.versioning, tag="20230829-1234", pr_number=None
    ),
)


@dataclass(frozen=True)
class TestStage:
    @staticmethod
    def build():
        return Stage(name="build", icon="🏗️")

    @staticmethod
    def test():
        return Stage(name="test", icon="📋")

    @staticmethod
    def deploy():
        return Stage(name="deploy", icon="🚀")


def get_config_values() -> dict:
    return config_values


def get_project() -> Project:
    return safe_load_project("test_projects/test_project.yml")


def get_project_execution() -> ProjectExecution:
    return ProjectExecution.run(get_project())


def get_deployment_strategy_project() -> Project:
    return safe_load_project("test_projects/test_project_deployment_strategy.yml")


def get_minimal_project() -> Project:
    return safe_load_project("test_projects/test_minimal_project.yml")


def get_project_without_swagger() -> Project:
    return safe_load_project("test_projects/test_project_without_swagger.yml")


def get_job_project() -> Project:
    return safe_load_project("test_projects/test_job_project.yml")


def get_cron_job_project() -> Project:
    return safe_load_project("test_projects/test_cron_job_project.yml")


def get_spark_project() -> Project:
    return safe_load_project("test_projects/test_spark_project.yml")


def safe_load_project(name: str) -> Project:
    return load_project(resource_path, Path(name), True, False, True)


def run_properties_with_plan(plan: RunPlan) -> RunProperties:
    run_properties = construct_run_properties(
        config=config_values,
        properties=properties_values,
        run_plan=plan,
        all_projects={get_minimal_project()},
    )

    return run_properties


def run_properties_prod_with_plan() -> RunProperties:
    plan = RunPlan.from_plan(
        {TestStage.deploy(): {ProjectExecution.run(get_minimal_project())}}
    )
    run_properties_prod = construct_run_properties(
        config=config_values,
        properties=properties_values,
        run_plan=plan,
        all_projects={get_minimal_project()},
    )
    return dataclasses.replace(
        run_properties_prod,
        target=Target.PRODUCTION,
        versioning=dataclasses.replace(
            RUN_PROPERTIES.versioning, tag="20230829-1234", pr_number=None
        ),
    )


def get_output() -> Output:
    return Output(
        success=True,
        message="build success",
        produced_artifact=Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE,
            revision="123",
            hash="a generated hash",
            producing_step="Producing Step",
            spec=DockerImageSpec(image="image:latest"),
        ),
    )


def get_project_with_stages(
    stage_config: dict, path: str = "deployment/project.yml", maintainers=None
):
    if maintainers is None:
        maintainers = ["Team1", "Team2"]
    stages = Stages.from_config(stage_config)
    return Project(
        "test", "Test project", path, None, stages, maintainers, None, None, None, None
    )


class MockRepository(Repository):
    def __init__(self, config: RepoConfig):
        self._config = config
        self._repo = Repo(Path("."))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    def find_projects(
        self, folder_pattern: str = "", config_folder: str = "deployment"
    ) -> list[str]:
        projects = Path(os.path.basename(root_test_path)).glob(
            f"*{folder_pattern}*/{config_folder}/{Project.project_yaml_file_name()}"
        )
        return sorted(map(str, projects))


def get_repo() -> Repository:
    config = RepoConfig.from_config(get_config_values())

    if "GITHUB_JOB" in os.environ:
        print("Running in github, falling back onto mock repository bypassing Git")
        return MockRepository(config)

    return Repository(config)


def assert_roundtrip(file_path: Path, actual_contents: str, overwrite: bool = False):
    if overwrite:
        if not file_path.exists():
            os.makedirs(file_path.parent, exist_ok=True)

        with open(file_path, "w+", encoding="utf-8") as file:
            file.write(actual_contents)
            assert not overwrite, "Should not commit with overwrite"

    with open(file_path, encoding="utf-8") as file:
        assert actual_contents == file.read()
