"""Versioning and upgrade utilities for mpyl projects.
### Writing an upgrade script

To write an upgrade script, create a new class that inherits from `Upgrader` and
implements the `upgrade` method. This class should then be added to the `UPGRADERS`
list in this module.

"""
import copy
import pkgutil
import re
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Generator
from typing import Optional

from deepdiff import DeepDiff
from ruamel.yaml.compat import ordereddict

from ..utilities.yaml import yaml_to_string, load_for_roundtrip

VERSION_FIELD = "mpylVersion"
BASE_RELEASE = "1.0.8"


@dataclass
class Release:
    major: int
    minor: int
    patch: int
    release_candidate: Optional[int] = None

    @staticmethod
    def from_string(version: str):
        parts = version.split(".")
        minor_parts = parts[2].split("rc")
        return Release(
            int(parts[0]),
            int(parts[1]),
            int(minor_parts[0]),
            int(minor_parts[1]) if len(minor_parts) > 1 else None,
        )

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}" + (
            f"rc{self.release_candidate}" if self.release_candidate else ""
        )


def get_releases() -> list[Release]:
    embedded_releases = pkgutil.get_data(__name__, "releases/releases.txt")
    if not embedded_releases:
        raise ValueError("File releases/releases.txt not found in package")
    releases = embedded_releases.decode("utf-8").strip().splitlines()
    return list(reversed(list(map(Release.from_string, releases))))


def get_latest_release() -> Release:
    return get_releases()[0]


def add_release(release: Release) -> None:
    releases_path = Path(__file__).parent / "releases/releases.txt"
    with open(releases_path, "a", encoding="utf-8") as releases_file:
        releases_file.write(str(f"\n{release}"))


def get_release_notes_base_path():
    return Path(__file__).parent.parent.parent.parent / "releases"


def get_release_notes_readme_path():
    return get_release_notes_base_path() / "README.md"


def get_release_notes_path(release: Release):
    return get_release_notes_base_path() / "notes" / f"{release}.md"


def render_release_notes() -> str:
    without_rcs = [rel for rel in get_releases() if rel.release_candidate is None]
    combined = "# Release notes\n\n"
    for release in without_rcs:
        combined += f"## MPyL {release}\n\n"

        file = f"{release}.md"
        notes = get_release_notes_path(release)
        if notes.exists():
            combined += "\n"
            text = notes.read_text("utf-8")

            if (
                re.match("^# ", text)
                or re.match("^## ", text)
                or re.match("^### ", text)
            ):
                raise ValueError(
                    f"{file} should not contain #, ## or ### because it messes up the TOC"
                )
            combined += text + "\n\n"
        combined += f"Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/{release})\n\n"
    return combined


class Upgrader(ABC):
    """Base class for upgrade scripts"""

    target_version: str

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


class UpgraderOne11(Upgrader):
    target_version = "1.0.11"


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
