import pkgutil

from src.mpyl.validation import validate
from tests.test_resources.test_data import config_values


class TestValidation:
    def test_validate_config_schema(self):
        schema_dict = pkgutil.get_data(
            __name__, "../src/mpyl/schema/mpyl_config.schema.yml"
        )

        assert schema_dict is not None
        validate(config_values, schema_dict.decode("utf-8"))
