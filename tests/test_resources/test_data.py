from pyaml_env import parse_config

from src.mpyl import Target
from src.mpyl.project import load_project
from src.mpyl.steps.models import RunProperties, VersioningProperties
from tests import root_test_path

resource_path = root_test_path / "test_resources"
config_values = parse_config(resource_path / "config.yml")

RUN_PROPERTIES = RunProperties("id", Target.PULL_REQUEST,
                               VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None),
                               config_values)

TEST_PROJECT = load_project(resource_path, "test_project.yml", False)
