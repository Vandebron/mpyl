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
            with open(filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)

        h = hash_sha256.hexdigest()
        print(f"hash of changes for ${self.name}: ${h}")
        return h
