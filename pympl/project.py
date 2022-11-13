import json
import pkgutil
from dataclasses import dataclass
from typing import Optional, TypeVar, Dict, Any

import jsonschema
import yaml
from mypy.checker import Generic

from pympl.target import Target

T = TypeVar('T')


@dataclass(frozen=True)
class TargetSpecificProperty(Generic[T]):
    pr: Optional[T]
    test: Optional[T]
    acceptance: Optional[T]
    production: Optional[T]
    all: Optional[T]

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
        return TargetSpecificProperty(pr=values.get('pr'), test=values.get('test'), acceptance=values.get('acceptance'),
                                      production=values.get('production'), all=values.get('all'))


@dataclass(frozen=True)
class KeyValueProperty(TargetSpecificProperty[str]):
    key: str

    @staticmethod
    def from_yaml(values: dict):
        return KeyValueProperty(key=values['key'], pr=values.get('pr'), test=values.get('test'),
                                acceptance=values.get('acceptance'), production=values.get('production'),
                                all=values.get('all'))


@dataclass(frozen=True)
class StageSpecificProperty(Generic[T]):
    build: Optional[T]
    test: Optional[T]
    deploy: Optional[T]
    postdeploy: Optional[T]


@dataclass(frozen=True)
class Stages(StageSpecificProperty[str]):

    @staticmethod
    def from_yaml(values: dict):
        return Stages(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass(frozen=True)
class Dependencies(StageSpecificProperty[list[str]]):
    @staticmethod
    def from_yaml(values: dict):
        return Dependencies(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                            postdeploy=values.get('postdeploy'))


@dataclass(frozen=True)
class Env:
    @staticmethod
    def from_yaml(values: list[dict]):
        return list(map(lambda v: KeyValueProperty.from_yaml(v), values))


@dataclass(frozen=True)
class Properties:
    env: list[KeyValueProperty]

    @staticmethod
    def from_yaml(values: Dict[Any, Any]):
        return Properties(env=list(map(lambda v: KeyValueProperty.from_yaml(v), values.get('env', []))))


@dataclass(frozen=True)
class Probe:
    path: TargetSpecificProperty[str]

    @staticmethod
    def from_yaml(values: dict):
        path = values['path']
        return Probe(path=TargetSpecificProperty.from_yaml(path))


@dataclass(frozen=True)
class Metrics:
    path: str
    enabled: bool

    @staticmethod
    def from_yaml(values: dict):
        return Metrics(path=values.get('path', '/metrics'), enabled=values.get('enabled', False))


@dataclass(frozen=True)
class Kubernetes:
    portMappings: dict[int, int]
    livenessProbe: Optional[Probe]
    metrics: Optional[Metrics]

    @staticmethod
    def from_yaml(values: dict):
        mappings = values.get('portMappings')
        liveness_probe = values.get('livenessProbe')
        metrics = values.get('metrics')
        return Kubernetes(portMappings=mappings if mappings else {},
                          livenessProbe=Probe.from_yaml(liveness_probe) if liveness_probe else None,
                          metrics=Metrics.from_yaml(metrics) if metrics else None)


@dataclass(frozen=True)
class Host:
    host: TargetSpecificProperty[str]
    tls: TargetSpecificProperty[str]
    whitelists: TargetSpecificProperty[list[str]]

    @staticmethod
    def from_yaml(values: dict):
        host = values.get('host')
        tls = values.get('tls')
        whitelists = values.get('whitelists')
        return Host(host=TargetSpecificProperty.from_yaml(host) if host else None,
                    tls=TargetSpecificProperty.from_yaml(tls) if tls else None,
                    whitelists=TargetSpecificProperty.from_yaml(whitelists) if whitelists else None)


@dataclass(frozen=True)
class Traefik:
    hosts: list[Host]

    @staticmethod
    def from_yaml(values: dict):
        hosts = values.get('hosts')
        return Traefik(hosts=(list(map(lambda h: Host.from_yaml(h), hosts) if hosts else [])))


@dataclass(frozen=True)
class Deployment:
    namespace: str
    properties: Properties
    kubernetes: Optional[Kubernetes]
    traefik: Optional[Traefik]

    @staticmethod
    def from_yaml(values: dict):
        props = values.get('properties')
        kubernetes = values.get('kubernetes')
        traefik = values.get('traefik')
        return Deployment(namespace=values['namespace'], properties=Properties.from_yaml(props) if props else None,
                          kubernetes=Kubernetes.from_yaml(kubernetes) if kubernetes else None,
                          traefik=Traefik.from_yaml(traefik) if traefik else None)


@dataclass(frozen=True)
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


def load_project(project_path: str, strict: bool = True) -> Optional[Project]:
    with open(project_path) as f:
        try:
            yaml_values = yaml.load(f, Loader=yaml.FullLoader)
            template = pkgutil.get_data(__name__, "schema/project.schema.json")
            if strict and template:
                schema = json.loads(template.decode('utf-8'))
                jsonschema.validate(yaml_values, schema)

            return Project.from_yaml(yaml_values, project_path)
        except jsonschema.exceptions.ValidationError as e:
            print(f'{project_path} does not comply with schema: ', e.message)
        except TypeError as e:
            import traceback
            traceback.print_exc()
            print(f'Type error', e, )
        except Exception as e:
            print(f'Failed to load {project_path}', e)

        return None
