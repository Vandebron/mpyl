import unittest
from io import StringIO

from ruamel.yaml import YAML  # type: ignore

from src.mpyl.steps.models import Output, Artifact, ArtifactType
from tests import root_test_path

yaml = YAML()
yaml.preserve_quotes = True


class TestDiscovery(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
