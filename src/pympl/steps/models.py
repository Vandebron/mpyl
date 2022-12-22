from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from ..project import Project
from ..stage import Stage
from ..target import Target
from ruamel.yaml import YAML, yaml_object  # type: ignore

yaml = YAML()


@dataclass(frozen=True)
class VersioningProperties:
    revision: str
    pr_number: Optional[str]
    tag: Optional[str]


@yaml_object(yaml)
@dataclass(frozen=True)
class BuildProperties:
    build_id: str
    target: Target
    git: VersioningProperties


@yaml_object(yaml)
class ArtifactType(Enum):
    def __eq__(self, other):
        return self.value == other.value

    @classmethod
    def from_yaml(cls, constructor, node):
        return ArtifactType(int(node.value.split('-')[1]))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(u'!ArtifactType',
                                            '{}-{}'.format(node._name_, node._value_)
                                            )

    DOCKER_IMAGE = 1
    JUNIT_TESTS = 2
    NONE = 3


@yaml_object(yaml)
@dataclass(frozen=True)
class Artifact:
    artifact_type: ArtifactType
    revision: str
    producing_step: str
    spec: dict


@yaml_object(yaml)
@dataclass(frozen=True)
class Input:
    project: Project
    build_properties: BuildProperties
    required_artifact: Optional[Artifact] = None

    def docker_image_tag(self):
        git = self.build_properties.git
        tag = f"pr-{git.pr_number}" if git.pr_number else git.tag
        return f"{self.project.name.lower()}:{tag}"


@yaml_object(yaml)
@dataclass()
class Output:
    success: bool
    message: str
    produced_artifact: Optional[Artifact] = None

    @staticmethod
    def path(target_path: str, stage: Stage):
        return Path(target_path, f"{stage.name}.yml")

    def write(self, target_path: str, stage: Stage):
        Path(target_path).mkdir(parents=True, exist_ok=True)
        with Output.path(target_path, stage).open(mode='w+') as file:
            yaml.dump(self, file)

    @staticmethod
    def try_read(target_path: str, stage: Stage):
        path = Output.path(target_path, stage)
        if path.exists():
            with open(path) as f:
                return yaml.load(f)
        return None


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    version: str
    stage: Stage

    def __str__(self) -> str:
        return f'{self.name}: {self.version}'
