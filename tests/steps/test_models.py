import pytest
from jsonschema import ValidationError
from pyaml_env import parse_config
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.steps.models import RunProperties, VersioningProperties
from tests import root_test_path

yaml = YAML()
yaml.preserve_quotes = True


class TestModels:
    resource_path = root_test_path / "test_resources"

    run_properties_values = parse_config(resource_path / "run_properties.yml")
    config_values = parse_config(resource_path / "mpyl_config.yml")

    def test_should_return_error_if_validation_fails(self):
        with pytest.raises(ValidationError) as excinfo:
            RunProperties.from_configuration(self.run_properties_values, self.config_values)

        assert "'user' is a required property" in excinfo.value.message

    def test_should_return_error_if_pr_number_or_tag_not_set(self):
        versioning = self.run_properties_values['build']['versioning']

        with pytest.raises(ValueError, match="Either pr_number or tag need to be set"):
            VersioningProperties(versioning['revision'], versioning['branch'], versioning['pr_number'],
                                 versioning['tag'])
