import dataclasses
import os
from pathlib import Path

from attr import dataclass

from src.mpyl.utilities.docker import DockerImageSpec
from src.mpyl.constants import (
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_RUN_PROPERTIES_FILE_NAME,
)
from src.mpyl.utilities.pyaml_env import parse_config

from src.mpyl.project import load_project, Target, Project, Stages, Stage
from src.mpyl.steps.models import (
    RunProperties,
    Output,
    ArtifactType,
    Artifact,
)
from src.mpyl.utilities.repo import Repository, RepoConfig
from tests import root_test_path

resource_path = root_test_path / "test_resources"
config_values = parse_config(resource_path / DEFAULT_CONFIG_FILE_NAME)
properties_values = parse_config(resource_path / DEFAULT_RUN_PROPERTIES_FILE_NAME)

RUN_PROPERTIES = RunProperties.from_configuration(properties_values, config_values)

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
    return safe_load_project("test_project.yml")


def get_minimal_project() -> Project:
    return safe_load_project("test_minimal_project.yml")


def get_job_project() -> Project:
    return safe_load_project("test_job_project.yml")


def get_cron_job_project() -> Project:
    return safe_load_project("test_cron_job_project.yml")


def get_spark_project() -> Project:
    return safe_load_project("test_spark_project.yml")


def safe_load_project(name: str) -> Project:
    return load_project(resource_path, Path(name), True, False, True)


def get_output() -> Output:
    return Output(
        success=True,
        message="build success",
        produced_artifact=Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE,
            revision="123",
            producing_step="Producing Step",
            spec=DockerImageSpec(image="image:latest"),
        ),
    )


def get_project_with_stages(stage_config: dict, path: str = "", maintainers=None):
    if maintainers is None:
        maintainers = ["Team1", "Team2"]
    stages = Stages.from_config(stage_config)
    return Project(
        "test", "Test project", path, stages, maintainers, None, None, None, None
    )


class MockRepository(Repository):
    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = "."

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    def find_projects(self, folder_pattern: str = "") -> list[str]:
        projects = Path(self.root_dir).glob(
            f"*{folder_pattern}*/{Project.project_yaml_path()}"
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
