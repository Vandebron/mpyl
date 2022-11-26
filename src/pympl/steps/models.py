from dataclasses import dataclass
from typing import Optional

from ..project import Project
from ..stage import Stage
from ..target import Target


@dataclass(frozen=True)
class VersioningProperties:
    pr_number: Optional[str]
    tag: Optional[str]


@dataclass(frozen=True)
class BuildProperties:
    build_id: str
    target: Target
    git: VersioningProperties


@dataclass(frozen=True)
class Input:
    project: Project
    build_properties: BuildProperties

    def docker_image_tag(self):
        git = self.build_properties.git
        tag = f"pr-{git.pr_number}" if git.pr_number else git.tag
        return f"{self.project.name.lower()}:{tag}"


@dataclass(frozen=True)
class Output:
    success: bool
    message: str


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    version: str
    stage: Stage

    def __str__(self) -> str:
        return f'{self.name}: {self.version}'
