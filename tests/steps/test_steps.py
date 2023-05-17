import logging
from io import StringIO
from logging import Logger

import pytest
from jsonschema import ValidationError
from pyaml_env import parse_config
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import DEFAULT_CONFIG_FILE_NAME
from src.mpyl.project import Project, Stages, Stage, Target, Dependencies
from src.mpyl.steps.models import Output, ArtifactType, RunProperties, VersioningProperties, ConsoleProperties
from src.mpyl.steps.steps import Steps
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip, get_output

yaml = YAML()


class TestSteps:
    resource_path = root_test_path / "test_resources"
    executor = Steps(logger=logging.getLogger(), properties=test_data.RUN_PROPERTIES)

    docker_image = get_output()
    build_project = test_data.get_project_with_stages({'build': 'Echo Build'}, path=str(resource_path))

    @staticmethod
    def _roundtrip(output) -> Output:
        stream = StringIO()
        yaml.dump(output, stream)
        output_string = stream.getvalue()
        return yaml.load(output_string)

    def test_output_no_artifact_roundtrip(self):
        output: Output = self._roundtrip(Output(success=True, message="build success"))

        assert output.produced_artifact is None
        assert output.message == "build success"

    def test_output_roundtrip(self):
        output: Output = self._roundtrip(self.docker_image)
        assert output.produced_artifact.artifact_type.name == "DOCKER_IMAGE"
        assert output.produced_artifact.spec == {'image': 'image:latest'}

    def test_write_output(self):
        stream = StringIO()
        yaml.dump(self.docker_image, stream)
        value = stream.getvalue()
        assert_roundtrip(test_resource_path / "deployment" / ".mpl" / "BUILD.yml", value)

    def test_find_required_output(self):
        found_artifact = Steps._find_required_artifact(self.build_project, ArtifactType.DOCKER_IMAGE)
        assert found_artifact == self.docker_image.produced_artifact

    def test_find_not_required_output(self):
        with pytest.raises(ValueError) as exc_info:
            Steps._find_required_artifact(self.build_project, ArtifactType.DEPLOYED_HELM_APP)
        assert str(exc_info.value) == 'Artifact ArtifactType.DEPLOYED_HELM_APP required for test not found'

    def test_find_required_output_should_handle_none(self):
        assert Steps._find_required_artifact(self.build_project, None) is None

    def test_should_return_error_if_stage_not_defined(self):
        steps = Steps(logger=Logger.manager.getLogger('logger'), properties=test_data.RUN_PROPERTIES)
        stages = Stages(build=None, test=None, deploy=None, postdeploy=None)
        project = Project('test', 'Test project', '', stages, [], None, None)
        output = steps.execute(stage=Stage.BUILD, project=project).output
        assert not output.success
        assert output.message == "Stage 'build' not defined on project 'test'"

    def test_should_return_error_if_config_invalid(self):
        config_values = parse_config(self.resource_path / DEFAULT_CONFIG_FILE_NAME)
        config_values['kubernetes']['rancher']['cluster']['test']['invalid'] = 'somevalue'
        properties = RunProperties("id", Target.PULL_REQUEST, VersioningProperties("", "feature/ARC-123", 1, None),
                                   config_values, ConsoleProperties("INFO", 130), True)
        with pytest.raises(ValidationError) as excinfo:
            Steps(logger=Logger.manager.getLogger('logger'), properties=properties)
        assert "('invalid' was unexpected)" in excinfo.value.message

    def test_should_succeed_if_executor_is_known(self):
        project = test_data.get_project_with_stages({'build': 'Echo Build'})
        result = self.executor.execute(stage=Stage.BUILD, project=project)
        assert result.output.success
        assert result.output.message == 'Built test'
        assert result.output.produced_artifact is None

    def test_should_fail_if_executor_is_not_known(self):
        project = test_data.get_project_with_stages({'build': 'Unknown Build'})
        result = self.executor.execute(stage=Stage.BUILD, project=project)
        assert not result.output.success
        assert result.output.message == "Executor 'Unknown Build' for 'build' not known or registered"

    def test_should_fail_if_maintainer_is_not_known(self):
        project = test_data.get_project_with_stages(stage_config={'build': 'Echo Build'}, path='',
                                                    maintainers=['Unknown Team'])

        result = self.executor.execute(stage=Stage.BUILD, project=project)
        assert not result.output.success
        assert result.output.message == "Maintainer(s) 'Unknown Team' not defined in config"

    def test_should_succeed_if_stage_is_not_known(self):
        project = test_data.get_project_with_stages(stage_config={'test': 'Some Test'})
        result = self.executor.execute(stage=Stage.BUILD, project=project)
        assert not result.output.success
        assert result.output.message == "Stage 'build' not defined on project 'test'"

    def test_should_run_post_deploy_cypress_step(self):
        stages = Stages.from_config({'postdeploy': 'Cypress Test'})
        project = Project('test', 'Test project', '', stages, [], None, Dependencies.from_config(
            {'postdeploy': ['specs/*.js']}))
        result = self.executor.execute(stage=Stage.POST_DEPLOY, project=project)
        assert result.output.success
