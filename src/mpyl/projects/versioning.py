"""Versioning and upgrade utilities for mpyl projects.
### Writing an upgrade script

To write an upgrade script, create a new class that inherits from `Upgrader` and
implements the `upgrade` method. This class should then be added to the `UPGRADERS`
list in this module.

"""
import copy
import pkgutil
from abc import ABC
from pathlib import Path
from typing import Optional, Generator

from deepdiff import DeepDiff
from ruamel.yaml.compat import ordereddict

from ..utilities.yaml import yaml_to_string, load_for_roundtrip

VERSION_FIELD = "mpylVersion"
BASE_RELEASE = "1.0.8"


def get_releases() -> list[str]:
    embedded_releases = pkgutil.get_data(__name__, "releases/releases.txt")
    if not embedded_releases:
        raise ValueError("File releases/releases.txt not found in package")
    releases = embedded_releases.decode("utf-8").strip().splitlines()
    return list(reversed(releases))


def get_latest_release() -> str:
    return get_releases()[0]


class Upgrader(ABC):
    """Base class for upgrade scripts"""

    target_version: str

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


class UpgraderOne11(Upgrader):
    target_version = "1.0.11"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


class UpgraderOne10(Upgrader):
    target_version = "1.0.10"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if found_deployment := previous_dict.get("deployment", {}):
            existing_namespace = found_deployment.get("namespace", None)
            if not existing_namespace:
                previous_dict["deployment"].insert(
                    0, "namespace", previous_dict["name"]
                )

        return previous_dict


class UpgraderOne9(Upgrader):
    target_version = "1.0.9"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        previous_dict.insert(3, VERSION_FIELD, self.target_version)
        return previous_dict


class UpgraderOne8(Upgrader):
    target_version = BASE_RELEASE

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


UPGRADERS = [UpgraderOne8(), UpgraderOne9(), UpgraderOne10(), UpgraderOne11()]


def get_entry_upgrader_index(
    current_version: str, upgraders: list[Upgrader]
) -> Optional[int]:
    next_index = next(
        (i for i, v in enumerate(upgraders) if v.target_version == current_version),
        None,
    )
    return next_index


def __get_version(project: dict) -> str:
    return project.get(VERSION_FIELD, "1.0.8")


def upgrade_to_latest(
    to_upgrade: ordereddict, upgraders: list[Upgrader]
) -> ordereddict:
    upgrade_index = get_entry_upgrader_index(__get_version(to_upgrade), upgraders)
    if upgrade_index is None:
        return to_upgrade

    upgraded = to_upgrade
    for i in range(upgrade_index, len(upgraders)):
        upgrader = upgraders[i]
        before_upgrade = copy.deepcopy(upgraded)
        upgraded = upgrader.upgrade(copy.deepcopy(before_upgrade))
        diff = DeepDiff(before_upgrade, upgraded, ignore_order=True, view="tree")
        if diff:
            upgraded[VERSION_FIELD] = upgrader.target_version
    return upgraded


def pretty_print(diff: DeepDiff) -> str:
    result = []
    if "dictionary_item_added" in diff:
        for key, value in diff["dictionary_item_added"].items():
            result.append(f"+ {key} -> '{value}'")
    if "dictionary_item_removed" in diff:
        for key, value in diff["dictionary_item_removed"].items():
            result.append(f"- {key} -> '{value}'")
    if "values_changed" in diff:
        for key, values in diff["values_changed"].items():
            new = values.get("new_value", None)
            old = values.get("old_value", None)
            result.append(f"  {key}: {f'{old} ->' if old else ''}{new if new else ''}")
    return "\n".join(result)


def check_upgrades_needed(
    file_path: list[Path],
) -> Generator[tuple[Path, DeepDiff], None, None]:
    for path in file_path:
        yield check_upgrade_needed(path)


def check_upgrade_needed(file_path: Path) -> tuple[Path, Optional[DeepDiff]]:
    loaded, _ = load_for_roundtrip(file_path)
    upgraded = upgrade_to_latest(loaded, UPGRADERS)
    diff = DeepDiff(loaded, upgraded, ignore_order=True, view="_delta")
    if diff:
        return file_path, diff
    return file_path, None


def upgrade_file(project_file: Path, upgraders: list[Upgrader]) -> Optional[str]:
    to_upgrade, yaml = load_for_roundtrip(project_file)
    upgraded = upgrade_to_latest(copy.deepcopy(to_upgrade), upgraders)
    return yaml_to_string(upgraded, yaml)
