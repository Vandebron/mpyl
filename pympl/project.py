from dataclasses import dataclass
from typing import Optional, TypeVar
import yaml

from pympl.target import Target

T = TypeVar('T')


@dataclass
class TargetSpecificProperty:
    pr: Optional[T]
    test: Optional[T]
    acceptance: Optional[T]
    production: Optional[T]
    all: Optional[T]


@dataclass
class KeyValueProperty(TargetSpecificProperty):
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
        return KeyValueProperty(key=values.get('key'), pr=values.get('pr'), test=values.get('test'),
                                acceptance=values.get('acceptance'), production=values.get('production'),
                                all=values.get('all'))


@dataclass
class Stages:
    build: Optional[str]
    test: Optional[str]
    deploy: Optional[str]
    postdeploy: Optional[str]

    @staticmethod
    def from_yaml(values: dict):
        return Stages(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass
class Env:
    @staticmethod
    def from_yaml(values: [dict]):
        return list(map(lambda v: KeyValueProperty.from_yaml(v), values))


@dataclass
class Properties:
    env: list[KeyValueProperty]

    @staticmethod
    def from_yaml(values: dict):
        return Properties(env=list(map(lambda v: KeyValueProperty.from_yaml(v), values.get('env', []))))


@dataclass
class Deployment:
    properties: Properties

    @staticmethod
    def from_yaml(values: dict):
        return Deployment(properties=Properties.from_yaml(values.get('properties')))


@dataclass
class Project:
    name: str
    description: str
    path: str
    stages: Stages
    maintainer: list[str]
    deployment: Optional[Deployment]

    @staticmethod
    def from_yaml(values: dict, project_path: str):
        return Project(name=values['name'], description=values['description'], path=project_path,
                       stages=Stages.from_yaml(values.get('stages', {})), maintainer=values.get('maintainer'),
                       deployment=Deployment.from_yaml(values.get('deployment')))


def load_project(project_path: str) -> Project:
    with open(project_path) as f:
        try:
            values = yaml.load(f, Loader=yaml.FullLoader)
            return Project.from_yaml(values, project_path)

        except Exception as e:
            print(f'Failed to load {project_path}', e)
