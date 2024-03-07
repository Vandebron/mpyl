"""This module contains the ProjectExecution class."""
import hashlib
from dataclasses import dataclass

from .project import Project


@dataclass(frozen=True)
class ProjectExecution:
    project: Project
    changed_files: frozenset[str]

    @property
    def name(self):
        return self.project.name

    @property
    def hashed_files(self):
        hash_sha256 = hashlib.sha256()

        for filename in self.changed_files:
            with open(filename, "rb") as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_sha256.update(chunk)

        changes_hash = hash_sha256.hexdigest()
        print(f"hash of changes for ${self.name}: ${changes_hash}")
        return changes_hash
