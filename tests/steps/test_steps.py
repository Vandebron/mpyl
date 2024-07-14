import logging
from logging import Logger
from typing import cast

import pytest
from jsonschema import ValidationError
from pyaml_env import parse_config
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import DEFAULT_CONFIG_FILE_NAME, RUN_ARTIFACTS_FOLDER
from src.mpyl.project import Project, Stages, Target
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.projects.versioning import yaml_to_string
from src.mpyl.run_plan import RunPlan
from src.mpyl.steps import build
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.steps.deploy.k8s import RenderedHelmChartSpec
from src.mpyl.steps.models import (
    Output,
    ArtifactType,
    RunProperties,
    VersioningProperties,
    ConsoleProperties,
    Artifact,
)
from src.mpyl.steps.steps import Steps
from src.mpyl.utilities.docker import DockerImageSpec
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip, get_output, RUN_PROPERTIES

yaml = YAML()


class TestSteps:
    resource_path = root_test_path / "test_resources"
    executor = Steps(
        logger=logging.getLogger(),
        properties=test_data.RUN_PROPERTIES,
        steps_collection=StepsCollection(logging.getLogger()),
        root_dir=resource_path,
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
        found_artifact = Steps._find_required_artifact(
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
            Steps._find_required_artifact(
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
            Steps._find_required_artifact(
                self.build_project, RUN_PROPERTIES.stages, None
            )
            is None
        )

    def test_should_return_error_if_stage_not_defined(self):
        steps = Steps(
            logger=Logger.manager.getLogger("logger"),
            properties=test_data.RUN_PROPERTIES,
            root_dir=self.resource_path,
        )
        stages = Stages(
            {"build": None, "test": None, "deploy": None, "postdeploy": None}
        )
        project = Project(
            "test", "Test project", "", None, stages, [], None, None, None, None
        )
        output = steps.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution.run(project),
        ).output
        assert not output.success
        assert output.message == "Stage 'build' not defined on project 'test'"

    def test_should_return_error_if_config_invalid(self):
        config_values = parse_config(self.resource_path / DEFAULT_CONFIG_FILE_NAME)
        config_values["kubernetes"]["clusters"][0]["name"] = {}
        properties = RunProperties(
            details=RUN_PROPERTIES.details,
            target=Target.PULL_REQUEST,
            versioning=VersioningProperties("", "feature/ARC-123", 1, None),
            config=config_values,
            console=ConsoleProperties("INFO", False, 130),
            stages=[],
            projects=set(),
            run_plan=RunPlan.empty(),
        )
        with pytest.raises(ValidationError) as excinfo:
            Steps(
                logger=Logger.manager.getLogger("logger"),
                properties=properties,
                root_dir=self.resource_path,
            )
        assert "{} is not of type 'string'" in excinfo.value.message

    def test_should_succeed_if_executor_is_known(self):
        project = test_data.get_project_with_stages(
            stage_config={"build": "Echo Build"},
            path="",
        )
        result = self.executor.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution.run(project),
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
            project_execution=ProjectExecution.run(project),
        )
        assert not result.output.success
        assert (
            result.output.message
            == "Executor 'Unknown Build' for 'build' not known or registered"
        )

    def test_should_fail_if_maintainer_is_not_known(self):
        project = test_data.get_project_with_stages(
            stage_config={"build": "Echo Build"}, path="", maintainers=["Unknown Team"]
        )

        result = self.executor.execute(
            stage=build.STAGE_NAME,
            project_execution=ProjectExecution.run(project),
        )
        assert not result.output.success
        assert (
            result.output.message
            == "Maintainer(s) 'Unknown Team' not defined in config"
        )

    def test_should_succeed_if_stage_is_not_known(self):
        project = test_data.get_project_with_stages(stage_config={"test": "Some Test"})
        result = self.executor.execute(
            stage="build",
            project_execution=ProjectExecution.run(project),
        )
        assert not result.output.success
        assert result.output.message == "Stage 'build' not defined on project 'test'"
