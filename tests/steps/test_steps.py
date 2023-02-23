from io import StringIO
from logging import Logger

import pytest
from jsonschema import ValidationError
from pyaml_env import parse_config
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.project import Project, Stages, Stage
from src.mpyl.steps import Target
from src.mpyl.steps.models import Output, Artifact, ArtifactType, RunProperties, VersioningProperties
from src.mpyl.steps.steps import Steps
from tests import root_test_path
from tests.test_resources import test_data

yaml = YAML()
yaml.preserve_quotes = True


class TestSteps:
    resource_path = root_test_path / "test_resources"

    @staticmethod
    def _roundtrip(output):
        stream = StringIO()
        yaml.dump(output, stream)
        output_string = stream.getvalue()
        return yaml.load(output_string)

    def test_output_no_artifact_roundtrip(self):
        output: Output = self._roundtrip(Output(success=True, message="build success"))

        assert output.produced_artifact is None
        assert output.message == "build success"

    def test_output_roundtrip(self):
        meta_data = {'a': 'b'}
        output: Output = self._roundtrip(Output(success=True, message="build success",
                                                produced_artifact=Artifact(artifact_type=ArtifactType.DOCKER_IMAGE,
                                                                           revision="123",
                                                                           producing_step="Producing Step",
                                                                           spec=meta_data)))
        assert output.produced_artifact.artifact_type.name == "DOCKER_IMAGE"
        assert output.produced_artifact.spec == meta_data

    def test_should_return_error_if_stage_not_defined(self):
        steps = Steps(logger=Logger.manager.getLogger('logger'), properties=test_data.RUN_PROPERTIES)
        stages = Stages(build=None, test=None, deploy=None, postdeploy=None)
        project = Project('test', 'Test project', '', stages, [], None, None)
        output = steps.execute(stage=Stage.BUILD, project=project)
        assert not output.success
        assert output.message == "Stage 'build' not defined on project 'test'"

    def test_should_return_error_if_stage_not_defined(self):
        config_values = parse_config(self.resource_path / "config.yml")
        config_values['kubernetes']['rancher']['cluster']['test']['invalid'] = 'somevalue'
        properties = RunProperties("id", Target.PULL_REQUEST, VersioningProperties("", 1, None), config_values)
        with pytest.raises(ValidationError) as excinfo:
            Steps(logger=Logger.manager.getLogger('logger'), properties=properties)
        assert "('invalid' was unexpected)" in excinfo.value.message
