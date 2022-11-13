from dataclasses import dataclass
from typing import Optional, TypeVar, Dict, Any
import yaml
from mypy.checker import Generic

from pympl.target import Target

T = TypeVar('T')


@dataclass
class TargetSpecificProperty(Generic[T]):
    pr: Optional[T]
    test: Optional[T]
    acceptance: Optional[T]
    production: Optional[T]
    all: Optional[T]


@dataclass
class KeyValueProperty(TargetSpecificProperty[str]):
    key: str

    def get_value(self, target: Target):
        if self.all:
            return self.all
        if target is Target.PULL_REQUEST:
            return self.pr
        if target is Target.PULL_REQUEST_BASE:
            return self.test
        if target is Target.ACCEPTANCE:
            return self.acceptance
        if target is Target.PRODUCTION:
            return self.production

    @staticmethod
    def from_yaml(values: dict):
        return KeyValueProperty(key=values['key'], pr=values.get('pr'), test=values.get('test'),
                                acceptance=values.get('acceptance'), production=values.get('production'),
                                all=values.get('all'))


@dataclass()
class StageSpecificProperty(Generic[T]):
    build: Optional[T]
    test: Optional[T]
    deploy: Optional[T]
    postdeploy: Optional[T]


@dataclass
class Stages(StageSpecificProperty[str]):

    @staticmethod
    def from_yaml(values: dict):
        return Stages(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass
class Dependencies(StageSpecificProperty[list[str]]):
    @staticmethod
    def from_yaml(values: dict):
        return Dependencies(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass
class Env:
    @staticmethod
    def from_yaml(values: list[dict]):
        return list(map(lambda v: KeyValueProperty.from_yaml(v), values))


@dataclass
class Properties:
    env: list[KeyValueProperty]

    @staticmethod
    def from_yaml(values: Dict[Any, Any]):
        return Properties(env=list(map(lambda v: KeyValueProperty.from_yaml(v), values.get('env', []))))


@dataclass
class Deployment:
    namespace: str
    properties: Properties

    @staticmethod
    def from_yaml(values: dict):
        props = values.get('properties')
        return Deployment(namespace=values['namespace'], properties=Properties.from_yaml(props) if props else None)


@dataclass
class Project:
    name: str
    description: str
    path: str
    stages: Stages
    maintainer: list[str]
    deployment: Optional[Deployment]
    dependencies: Optional[Dependencies]

    @staticmethod
    def from_yaml(values: dict, project_path: str):
        deployment = values.get('deployment')
        dependencies = values.get('dependencies')
        return Project(name=values['name'], description=values['description'], path=project_path,
                       stages=Stages.from_yaml(values.get('stages', {})), maintainer=values['maintainer'],
                       deployment=Deployment.from_yaml(deployment) if deployment else None,
                       dependencies=Dependencies.from_yaml(dependencies) if dependencies else None)


def load_project(project_path: str) -> Optional[Project]:
    with open(project_path) as f:
        try:
            values = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(f'Failed to load {project_path}', e)

        return Project.from_yaml(values, project_path)
