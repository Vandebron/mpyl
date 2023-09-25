"""Utilities for working with YAML files."""
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.compat import ordereddict


def yaml_to_string(serializable: object, yaml: YAML) -> str:
    with StringIO() as stream:
        yaml.dump(serializable, stream)
        return stream.getvalue()


def yaml_for_roundtrip() -> YAML:
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # type: ignore
    yaml.preserve_quotes = True  # type: ignore
    return yaml


def load_for_roundtrip(project_file: Path) -> tuple[ordereddict, YAML]:
    """Load a YAML file for roundtrip editing, altering the original file as little as possible."""
    yaml = yaml_for_roundtrip()
    with project_file.open(encoding="utf-8") as file:
        dictionary = yaml.load(file)
        return dictionary, yaml
