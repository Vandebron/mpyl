from pyaml_env import parse_config

from src.mpyl import Target
from src.mpyl.steps.models import RunProperties, VersioningProperties

config_values = parse_config("config.yml")

RUN_PROPERTIES = RunProperties("id", Target.PULL_REQUEST,
                               VersioningProperties("2ad3293a7675d08bc037ef0846ef55897f38ec8f", "1234", None),
                               config_values)
