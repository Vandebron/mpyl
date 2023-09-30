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

from ..utilities.yaml import yaml_to_string, load_for_roundtrip, yaml_for_roundtrip

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


class ProjectUpgraderOne31(Upgrader):
    target_version = "1.3.1"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if kubernetes := previous_dict.get("deployment", {}).get("kubernetes", {}):
            if "cmd" in kubernetes:
                kubernetes["command"] = kubernetes.pop("cmd")
        return previous_dict


class ProjectUpgraderOne11(Upgrader):
    target_version = "1.0.11"


class ProjectUpgraderOne10(Upgrader):
    target_version = "1.0.10"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if found_deployment := previous_dict.get("deployment", {}):
            existing_namespace = found_deployment.get("namespace", None)
            if not existing_namespace:
                previous_dict["deployment"].insert(
                    0, "namespace", previous_dict["name"]
                )

        return previous_dict


class ProjectUpgraderOne9(Upgrader):
    target_version = "1.0.9"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        previous_dict.insert(3, VERSION_FIELD, self.target_version)
        return previous_dict


class ProjectUpgraderOne8(Upgrader):
    target_version = BASE_RELEASE

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


PROJECT_UPGRADERS = [
    ProjectUpgraderOne8(),
    ProjectUpgraderOne9(),
    ProjectUpgraderOne10(),
    ProjectUpgraderOne11(),
    ProjectUpgraderOne31(),
]


class ConfigUpgraderOne31(Upgrader):
    target_version = "1.3.0"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        whitelists = previous_dict.get("whiteLists", {})
        existing_addresses = whitelists.get("addresses")
        if existing_addresses:
            whitelists.pop("addresses")
            new_addresses = list(
                address
                if address.get("values") is None
                else {"name": address["name"], "all": address["values"]}
                for address in existing_addresses
            )
            previous_dict["whiteLists"].insert(1, "addresses", new_addresses)
        return previous_dict


class ConfigUpgraderOne30(Upgrader):
    target_version = "1.3.0"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if "cvs" not in previous_dict:
            return previous_dict

        index = list(previous_dict).index("cvs")
        cvs = previous_dict.pop("cvs")
        previous_dict.insert(index, "vcs", cvs)

        previous_docker_dict = previous_dict["docker"]
        default_host_name = copy.deepcopy(previous_docker_dict["registry"]["hostName"])
        previous_docker_dict.insert(0, "defaultRegistry", default_host_name)
        previous_docker_dict.insert(1, "registries", [previous_docker_dict["registry"]])
        previous_docker_dict.pop("registry")
        previous_dict["docker"] = previous_docker_dict
        return previous_dict


class ConfigUpgraderOne9(Upgrader):
    target_version = "1.0.9"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        previous_dict.insert(0, VERSION_FIELD, self.target_version)
        return previous_dict


class ConfigUpgraderOne8(Upgrader):
    target_version = BASE_RELEASE

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


CONFIG_UPGRADERS = [
    ConfigUpgraderOne8(),
    ConfigUpgraderOne9(),
    ConfigUpgraderOne30(),
    ConfigUpgraderOne31(),
]


class PropertiesUpgraderOne30(Upgrader):
    target_version = "1.3.0"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        if "stages" in previous_dict:
            return previous_dict

        previous_dict.insert(
            0,
            "stages",
            [
                {"name": "build", "icon": "🏗️"},
                {"name": "test", "icon": "📋"},
                {"name": "deploy", "icon": "🚀"},
                {"name": "postdeploy", "icon": "🦺"},
            ],
        )
        previous_dict.move_to_end("stages", last=True)
        return previous_dict


class PropertiesUpgraderOne9(Upgrader):
    target_version = "1.0.9"

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        previous_dict.insert(0, VERSION_FIELD, self.target_version)
        return previous_dict


class PropertiesUpgraderOne8(Upgrader):
    target_version = BASE_RELEASE

    def upgrade(self, previous_dict: ordereddict) -> ordereddict:
        return previous_dict


PROPERTIES_UPGRADERS = [
    PropertiesUpgraderOne8(),
    PropertiesUpgraderOne9(),
    PropertiesUpgraderOne30(),
]


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


def pretty_print_value(value) -> str:
    print_yaml = yaml_for_roundtrip()
    if isinstance(value, (dict, list, set)):
        return f"\n```\n{yaml_to_string(value, print_yaml)}```"
    return f"`{value}`\n"


def pretty_print(diff: DeepDiff) -> str:
    result = []
    if "dictionary_item_added" in diff:
        for key, value in diff["dictionary_item_added"].items():
            result.append(f"➕ {key} -> {pretty_print_value(value)}")
    if "dictionary_item_removed" in diff:
        for key, value in diff["dictionary_item_removed"].items():
            result.append(f"➖ {key} -> {pretty_print_value(value)}")
    if "values_changed" in diff:
        for key, values in diff["values_changed"].items():
            new = values.get("new_value", None)
            old = values.get("old_value", None)
            result.append(f"  {key}: {f'{old} ->' if old else ''}{new if new else ''}")
    return "\n".join(result)


def check_upgrades_needed(
    file_path: list[Path], upgraders: list[Upgrader]
) -> Generator[tuple[Path, DeepDiff], None, None]:
    for path in file_path:
        yield check_upgrade_needed(path, upgraders)


def check_upgrade_needed(
    file_path: Path, upgraders: list[Upgrader]
) -> tuple[Path, Optional[DeepDiff]]:
    loaded, _ = load_for_roundtrip(file_path)
    upgraded = upgrade_to_latest(loaded, upgraders)
    diff = DeepDiff(loaded, upgraded, ignore_order=True, view="_delta")
    if diff:
        return file_path, diff
    return file_path, None


def upgrade_file(project_file: Path, upgraders: list[Upgrader]) -> Optional[str]:
    to_upgrade, yaml = load_for_roundtrip(project_file)
    upgraded = upgrade_to_latest(copy.deepcopy(to_upgrade), upgraders)
    return yaml_to_string(upgraded, yaml)
