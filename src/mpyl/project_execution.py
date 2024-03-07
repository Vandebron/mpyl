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
    def hashed_changes(self):
        def sha256(filename: str):
            with open(filename, "rb") as file:
                return hashlib.file_digest(file, "sha256").hexdigest()

        # what's better than hashing once? hashing twice!
        hash_sha256 = hashlib.sha256()
        for changed_file in self.changed_files:
            hash_sha256.update(sha256(changed_file))

        changes_hash = hash_sha256.hexdigest()
        print(f"hash of changes for ${self.name}: ${changes_hash}")
        return changes_hash
