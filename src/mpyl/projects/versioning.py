"""Versioning and upgrade utilities for mpyl projects."""
import pkgutil
from io import StringIO
from pathlib import Path
from typing import Optional
import copy

from deepdiff import DeepDiff
from ruamel.yaml import YAML
from ruamel.yaml.compat import ordereddict


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


class Upgrader:
    target_version: str

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


class Upgrader11(Upgrader):
    target_version = "1.0.11"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


class Upgrader10(Upgrader):
    target_version = "1.0.10"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if found_deployment := previous_dict.get("deployment", {}):
            existing_namespace = found_deployment.get("namespace", None)
            if not existing_namespace:
                previous_dict["deployment"].insert(
                    0, "namespace", previous_dict["name"]
                )

        return previous_dict


class Upgrader9(Upgrader):
    target_version = "1.0.9"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        previous_dict.insert(3, "mpylVersion", self.target_version)
        return previous_dict


class Upgrader8(Upgrader):
    target_version = "1.0.8"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


upgraders = [Upgrader8(), Upgrader9(), Upgrader10(), Upgrader11()]


def get_next_upgrader(current_version: str) -> Optional[Upgrader]:
    next_index = next(
        (i for i, v in enumerate(upgraders) if v.target_version == current_version),
        None,
    )
    if next_index is not None:
        return upgraders[next_index + 1]
    return None


def __get_version(project: dict) -> str:
    return project.get("mpylVersion", "1.0.8")


def upgrade_file(project_file: Path) -> Optional[str]:
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # type: ignore
    yaml.preserve_quotes = True  # type: ignore
    with project_file.open(encoding="utf-8") as file:
        to_upgrade: ordereddict = yaml.load(file)
        current_version = __get_version(to_upgrade)
        next_upgrader = get_next_upgrader(current_version)
        if next_upgrader:
            upgraded = next_upgrader.upgrade(copy.deepcopy(to_upgrade))
            diff = DeepDiff(upgraded, to_upgrade, ignore_order=True)
            if diff:
                upgraded["mpylVersion"] = next_upgrader.target_version
                return yaml_to_string(upgraded, yaml)
            return None
        return None


def upgrade(project_file: Path, target_path: Optional[Path] = None):
    upgraded = upgrade_file(project_file)
    if upgraded:
        (target_path or project_file).write_text(upgraded, encoding="utf-8")
