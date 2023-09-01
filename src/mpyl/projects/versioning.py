"""Versioning and upgrade utilities for mpyl projects."""
import pkgutil
from io import StringIO

from ruamel.yaml import YAML


def get_releases() -> list[str]:
    embedded_releases = pkgutil.get_data(__name__, "releases/releases.txt")
    if not embedded_releases:
        raise ValueError("File releases/releases.txt not found in package")
    releases = embedded_releases.decode("utf-8").strip().splitlines()
    return list(reversed(releases))


def get_latest_release() -> str:
    return get_releases()[0]


def yaml_to_string(serializable: object, yaml: YAML) -> str:
    with StringIO() as stream:
        yaml.dump(serializable, stream)
        return stream.getvalue()
