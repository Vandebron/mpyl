import logging
from logging import Logger
from typing import cast

import pytest
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import RUN_ARTIFACTS_FOLDER
from src.mpyl.project import Project, Stages
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.projects.versioning import yaml_to_string
from src.mpyl.steps import build
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.steps.deploy.k8s import RenderedHelmChartSpec
from src.mpyl.steps.models import (
    Output,
    ArtifactType,
    Artifact,
)
from src.mpyl.steps.executor import Executor
from src.mpyl.utilities.docker import DockerImageSpec
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip, get_output, RUN_PROPERTIES

yaml = YAML()


class TestSteps:
    resource_path = root_test_path / "test_resources"
    executor = Executor(
        logger=logging.getLogger(),
        properties=test_data.RUN_PROPERTIES,
        steps_collection=StepsCollection(logging.getLogger()),
    )

    docker_image = get_output()
    build_project = test_data.get_project_with_stages(
        {"build": "Echo Build"}, path=str(resource_path / "deployment" / "project.yml")
    )

    @staticmethod
    def _roundtrip(output) -> Output:
        output_string = yaml_to_string(output, yaml)
        return yaml.load(output_string)

    def test_output_no_artifact_roundtrip(self):
        output: Output = self._roundtrip(Output(success=True, message="build success"))

        assert output.produced_artifact is None
        assert output.message == "build success"

    def test_output_roundtrip(self):
        output: Output = self._roundtrip(self.docker_image)
        assert output.produced_artifact is not None
        assert output.produced_artifact.artifact_type.name == "DOCKER_IMAGE"
        assert (
            cast(DockerImageSpec, output.produced_artifact.spec).image == "image:latest"
        )

    def test_write_output(self):
        build_yaml = yaml_to_string(self.docker_image, yaml)
        assert_roundtrip(
            test_resource_path / "deployment" / RUN_ARTIFACTS_FOLDER / "build.yml",
            build_yaml,
        )

    def test_write_deploy_output(self):
        output = Output(
            success=True,
            message="deploy success  success",
            produced_artifact=Artifact(
                artifact_type=ArtifactType.KUBERNETES_MANIFEST,
                revision="123",
                hash="a generated hash",
                producing_step="Producing Step",
                spec=RenderedHelmChartSpec("target/template.yml"),
            ),
        )

        assert_roundtrip(
            test_resource_path / "deployment" / RUN_ARTIFACTS_FOLDER / "deploy.yml",
            yaml_to_string(output, yaml),
        )

    def test_find_required_output(self):
        found_artifact = Executor._find_required_artifact(
            self.build_project, RUN_PROPERTIES.stages, ArtifactType.DOCKER_IMAGE
        )
        assert found_artifact is not None
        assert self.docker_image.produced_artifact is not None
        assert (
            cast(DockerImageSpec, found_artifact.spec).image
            == cast(DockerImageSpec, self.docker_image.produced_artifact.spec).image
        )

    def test_find_not_required_output(self):
        with pytest.raises(ValueError) as exc_info:
            Executor._find_required_artifact(
                self.build_project,
                RUN_PROPERTIES.stages,
                ArtifactType.DEPLOYED_HELM_APP,
            )
        assert (
            str(exc_info.value)
            == "Artifact ArtifactType.DEPLOYED_HELM_APP required for test not found"
        )

    def test_find_required_output_should_handle_none(self):
        assert (
            Executor._find_required_artifact(
                self.build_project, RUN_PROPERTIES.stages, None
            )
            is None
        )

    def test_should_return_error_if_stage_not_defined(self):
        steps = Executor(
            logger=Logger.manager.getLogger("logger"),
            properties=test_data.RUN_PROPERTIES,
        )
        stages = Stages(
            {"build": None, "test": None, "deploy": None, "postdeploy": None}
        )
        project = Project(
            "test", "Test project", "", None, stages, [], None, None, None, None
        )
        output = steps.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution(
                project=project,
                changed_files=frozenset(),
                hashed_changes=None,
                cached=False,
            ),
        ).output
        assert not output.success
        assert output.message == "Stage 'build' not defined on project 'test'"

    def test_should_succeed_if_executor_is_known(self):
        project = test_data.get_project_with_stages(
            stage_config={"build": "Echo Build"},
            path=str(self.resource_path / "metapath" / "project.yml"),
        )
        result = self.executor.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution(
                project=project,
                changed_files=frozenset(),
                hashed_changes=None,
                cached=False,
            ),
        )
        assert result.output.success
        assert result.output.message == "Built test"
        assert result.output.produced_artifact is not None
        assert (
            result.output.produced_artifact.artifact_type == ArtifactType.DOCKER_IMAGE
        )

    def test_should_fail_if_executor_is_not_known(self):
        project = test_data.get_project_with_stages({"build": "Unknown Build"})
        result = self.executor.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution(
                project=project,
                changed_files=frozenset(),
                hashed_changes=None,
                cached=False,
            ),
        )
        assert not result.output.success
        assert (
            result.output.message
            == "Executor 'Unknown Build' for 'build' not known or registered"
        )

    def test_should_succeed_if_stage_is_not_known(self):
        project = test_data.get_project_with_stages(stage_config={"test": "Some Test"})
        result = self.executor.execute(
            stage="build",
            project_execution=ProjectExecution(
                project=project,
                changed_files=frozenset(),
                hashed_changes=None,
                cached=False,
            ),
        )
        assert not result.output.success
        assert result.output.message == "Stage 'build' not defined on project 'test'"
