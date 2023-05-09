from pathlib import Path

from src.mpyl.validation import validate
from src.mpyl.utilities.pyaml_env import parse_config

EXAMPLE_FILE = "mpyl_config.example.yml"
config = parse_config(EXAMPLE_FILE)
SCHEMA_FILE = "src/mpyl/schema/mpyl_config.schema.yml"
schema = Path(SCHEMA_FILE).read_text("utf-8")
print(f"Validating {EXAMPLE_FILE} against {SCHEMA_FILE}")
validate(config, schema)
