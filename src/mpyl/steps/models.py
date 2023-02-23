""" Model representation of run-specific configuration. """

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict

from ruamel.yaml import YAML, yaml_object  # type: ignore

from ..project import Project, Stage
from ..steps import Target

yaml = YAML()


@dataclass(frozen=True)
class VersioningProperties:
    revision: str
    pr_number: Optional[int]
    tag: Optional[str]

    def __post_init__(self):
        if not self.pr_number and not self.tag:
            raise ValueError('Either pr_number or tag need to be set')

    @property
    def identifier(self):
        return f'pr-{self.pr_number}' if self.pr_number else self.tag


@yaml_object(yaml)
@dataclass(frozen=True)
class RunProperties:
    """ Contains information that is specific to a particular run of the pipeline
    """
    build_id: str
    """Uniquely identifies the run. Typically a monotonically increasing number"""
    target: Target
    """The deploy target"""
    versioning: VersioningProperties
    config: dict
    """Globally specified configuration, to be used by specific steps. Complies with the schema as
    specified in `mpyl_config.schema.yml`
     """

    @staticmethod
    def from_configuration(run_properties: Dict, config: Dict):
        build = run_properties['build']
        versioning = build['versioning']
        return RunProperties(build_id=build['run']['id'], target=Target(build['parameters']['deploy_target']),
                             versioning=VersioningProperties(versioning['revision'], int(versioning.get('pr_number')),
                                                             versioning.get('tag')), config=config)


@yaml_object(yaml)
@dataclass(frozen=True)
class ArtifactType(Enum):
    def __eq__(self, other):
        return self.value == other.value

    @classmethod
    def from_yaml(cls, _, node):
        return ArtifactType(int(node.value.split('-')[1]))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar('!ArtifactType',
                                            f'{node._name_}-{node._value_}')  # pylint: disable=protected-access

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
    run_properties: RunProperties
    required_artifact: Optional[Artifact] = None
    dry_run: bool = False


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
        with Output.path(target_path, stage).open(mode='w+', encoding='utf-8') as file:
            yaml.dump(self, file)

    @staticmethod
    def try_read(target_path: str, stage: Stage):
        path = Output.path(target_path, stage)
        if path.exists():
            with open(path, encoding='utf-8') as file:
                return yaml.load(file)
        return None


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    version: str
    stage: Stage

    def __str__(self) -> str:
        return f'{self.name}: {self.version}'


def input_to_artifact(artifact_type: ArtifactType, step_input: Input, spec: dict):
    return Artifact(artifact_type=artifact_type, revision=step_input.run_properties.versioning.revision,
                    producing_step=step_input.project.name, spec=spec)
