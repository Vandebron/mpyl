from mpyl import parse_config
from mpyl.steps.models import RunProperties
from tests import root_test_path

class TestDocker:
    resource_path = root_test_path / 'projects' / 'ephemeral' / 'deployment'

    def test_replace_default_with_none(self):
        yaml_values = parse_config(self.resource_path / 'project.yml')
        # RunProperties.from_configuration(yaml_values)
        print(yaml_values)
        assert not yaml_values['deployment']['properties']['env']['key1']
        assert yaml_values['deployment']['properties']['env'][] == 'fallback'
