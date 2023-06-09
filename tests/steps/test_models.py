import pytest
from jsonschema import ValidationError
from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_RUN_PROPERTIES_FILE_NAME
from src.mpyl.steps.models import RunProperties, VersioningProperties
from src.mpyl.utilities.pyaml_env import parse_config
from tests import root_test_path

yaml = YAML()


class TestModels:
    resource_path = root_test_path / "test_resources"

    run_properties_values = parse_config(resource_path / DEFAULT_RUN_PROPERTIES_FILE_NAME)
    config_values = parse_config(resource_path / DEFAULT_CONFIG_FILE_NAME)

    def test_should_return_error_if_validation_fails(self):
        with pytest.raises(ValidationError) as excinfo:
            run_properties = self.run_properties_values
            run_properties['build']['run']['user'] = 5
            RunProperties.from_configuration(run_properties, self.config_values)

        assert "5 is not of type 'string'" in excinfo.value.message

    def test_should_return_error_if_pr_number_or_tag_not_set(self):
        versioning = self.run_properties_values['build']['versioning']

        with pytest.raises(ValueError, match="pr_number"):
            VersioningProperties(versioning['revision'], versioning['branch'], None, None)
