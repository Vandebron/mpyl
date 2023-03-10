from pathlib import Path

from pyaml_env import parse_config

from src.mpyl.project import load_project, Target, Project, Stages
from src.mpyl.steps.models import RunProperties, VersioningProperties, RunContext, Output, ArtifactType, Artifact
from src.mpyl.utilities.repo import Repository, RepoConfig
from tests import root_test_path

resource_path = root_test_path / "test_resources"
config_values = parse_config(resource_path / "config.yml")

RUN_PROPERTIES = RunProperties(
    RunContext("id", "http://localhost/run", "http://localhost/changes", "http://localhost/tests", "somebody",
               "sam@vandebron.nl"),
    Target.PULL_REQUEST,
    VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "feature/ARC-123-branch", 1234, None),
    config_values)


def get_project() -> Project:
    return load_project(resource_path, "test_project.yml", False)


def get_output() -> Output:
    return Output(success=True, message="build success",
                  produced_artifact=Artifact(artifact_type=ArtifactType.DOCKER_IMAGE, revision="123",
                                             producing_step="Producing Step", spec={'image': 'image:latest'}))


def get_project_with_stages(stage_config: dict, path: str = ''):
    stages = Stages.from_config(stage_config)
    return Project('test', 'Test project', path, stages, [], None, None)


def get_repo() -> Repository:
    return Repository(RepoConfig({'cvs': {'git': {'mainBranch': 'main'}}}))


def assert_roundtrip(file_path: Path, expected_contents: str, overwrite: bool = False):
    if overwrite:
        with open(file_path, 'w+', encoding='utf-8') as file:
            file.write(expected_contents)
            assert not overwrite, "Should not commit with overwrite"

    with open(file_path, encoding='utf-8') as file:
        assert file.read() == expected_contents
