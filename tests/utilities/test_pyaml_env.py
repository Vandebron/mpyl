from src.mpyl.utilities.pyaml_env import parse_config
from tests import root_test_path


class TestPyYamlEnv:
    resource_path = root_test_path / "test_resources"

    def test_replace_default_with_none(self):
        yaml_values = parse_config(self.resource_path / "env_replace.yml")
        assert not yaml_values['root']['key1']
        assert yaml_values['root']['key2'] == 'fallback'
