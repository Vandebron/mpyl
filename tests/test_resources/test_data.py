import os
from pathlib import Path

from src.mpyl.constants import DEFAULT_CONFIG_FILE_NAME
from src.mpyl.utilities.pyaml_env import parse_config

from src.mpyl.project import load_project, Target, Project, Stages
from src.mpyl.steps.models import RunProperties, VersioningProperties, RunContext, Output, ArtifactType, Artifact, \
    ConsoleProperties
from src.mpyl.utilities.repo import Repository, RepoConfig
from tests import root_test_path

resource_path = root_test_path / "test_resources"
config_values = parse_config(resource_path / DEFAULT_CONFIG_FILE_NAME)

RUN_PROPERTIES = RunProperties(
    RunContext("id", "http://localhost/run", "http://localhost/changes", "http://localhost/tests", "somebody",
               "sam@vandebron.nl"),
    Target.PULL_REQUEST,
    VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "feature/ARC-123-branch", 1234, None),
    config_values,
    ConsoleProperties("INFO", 130))


def get_config_values() -> dict:
    return config_values


def get_project() -> Project:
    return load_project(resource_path, Path("test_project.yml"), True)


def get_minimal_project() -> Project:
    return load_project(resource_path, Path("test_minimal_project.yml"), True)


def get_job_project() -> Project:
    return load_project(resource_path, Path("test_job_project.yml"), True)


def get_cron_job_project() -> Project:
    return load_project(resource_path, Path("test_cron_job_project.yml"), True)


def get_spark_project() -> Project:
    return load_project(resource_path, Path("test_spark_project.yml"), True)


def get_output() -> Output:
    return Output(success=True, message="build success",
                  produced_artifact=Artifact(artifact_type=ArtifactType.DOCKER_IMAGE, revision="123",
                                             producing_step="Producing Step", spec={'image': 'image:latest'}))


def get_project_with_stages(stage_config: dict, path: str = ''):
    stages = Stages.from_config(stage_config)
    return Project('test', 'Test project', path, stages, [], None, None)


class MockRepository(Repository):

    def __init__(self, config: RepoConfig):
        self._config = config
        self._root_dir = '.'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    def find_projects(self, folder_pattern: str = '') -> list[str]:
        projects = Path(self.root_dir()).glob(f'*{folder_pattern}*/{Project.project_yaml_path()}')
        return sorted(map(str, projects))


def get_repo() -> Repository:
    config = RepoConfig({'cvs': {'git': {'mainBranch': 'main'}}})

    if 'GITHUB_JOB' in os.environ:
        print("Running in github, falling back onto mock repository bypassing Git")
        return MockRepository(config)

    return Repository(config)


def assert_roundtrip(file_path: Path, actual_contents: str, overwrite: bool = False):
    if overwrite:
        with open(file_path, 'w+', encoding='utf-8') as file:
            file.write(actual_contents)
            assert not overwrite, "Should not commit with overwrite"

    with open(file_path, encoding='utf-8') as file:
        assert actual_contents == file.read()
