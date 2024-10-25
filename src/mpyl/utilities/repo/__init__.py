import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...project import Project


@dataclass(frozen=True)
class Changeset:
    sha: str
    """Git hash for this revision"""
    _files_touched: dict[str, str]

    def files_touched(self, status: Optional[set[str]] = None):
        if not status or len(status) == 0:
            return set(self._files_touched.keys())

        return {file for file, s in self._files_touched.items() if s in status}

    @staticmethod
    def from_file(logger: logging.Logger, sha: str, changed_files_path: str):
        with open(changed_files_path, encoding="utf-8") as file:
            logger.debug(f"Creating Changeset based on changed files in {changed_files_path}")
            changed_files = json.load(file)
            return Changeset(sha=sha, _files_touched=changed_files)

    @staticmethod
    def from_diff(sha: str, diff: set[str]):
        changes = {}
        for line in diff:
            parts = line.split("\t")
            if len(parts) == 2:
                changes[parts[1]] = parts[0]
            elif len(parts) == 3 and parts[0].startswith("R"):
                changes[parts[2]] = "R"
            else:
                logging.warning(f"Skipping unparseable diff output line {line}")

        return Changeset(sha, changes)

    @staticmethod
    def with_untracked_files(sha: str, diff: set[str], untracked_files: set[str]):
        changes = {}
        for line in diff:
            parts = line.split("\t")
            changes[parts[1]] = parts[0]

        for file in untracked_files:
            changes[file] = "U"

        return Changeset(sha, changes)

    @staticmethod
    def empty(sha: str):
        return Changeset(sha=sha, _files_touched={})


class Repository:  # pylint: disable=too-many-public-methods
    def __init__(self, path: Path):
        self._path = path

    @property
    def root_dir(self) -> Path:
        return Path(self._path)

    def find_projects(self, folder_pattern: str = "") -> list[str]:
        # FIXME replace repo.git.ls_files with a filesystem path traversal
        return []
        # """
        # returns a set of all project.yml files
        # :param folder_pattern: project paths are filtered on this pattern
        # """
        # folder = f"*{folder_pattern}*/{self.config.project_sub_folder}"
        # projects_pattern = f"{folder}/{Project.project_yaml_file_name()}"
        # overrides_pattern = f"{folder}/{Project.project_overrides_yaml_file_pattern()}"
        #
        # def files(pattern: str):
        #     return set(self._repo.git.ls_files(pattern).splitlines())
        #
        # def deleted(pattern: str):
        #     return set(self._repo.git.ls_files("-d", pattern).splitlines())
        #
        # projects = files(projects_pattern) | files(overrides_pattern)
        # deleted = deleted(projects_pattern) | deleted(overrides_pattern)
        #
        # return sorted(projects - deleted)
