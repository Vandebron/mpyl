import json
import logging
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar, Dict, Any

import jsonschema
from kubernetes.client import V1Probe, ApiClient
from mypy.checker import Generic
from ruamel.yaml import YAML

from .stage import Stage
from .target import Target

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
        if target == Target.PULL_REQUEST:
            return self.pr
        if target == Target.PULL_REQUEST_BASE:
            return self.test
        if target == Target.ACCEPTANCE:
            return self.acceptance
        if target == Target.PRODUCTION:
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

    def for_stage(self, stage: Stage) -> Optional[T]:
        if stage == Stage.BUILD:
            return self.build
        if stage == Stage.TEST:
            return self.test
        if stage == Stage.DEPLOY:
            return self.deploy
        return self.postdeploy


@dataclass(frozen=True)
class Stages(StageSpecificProperty[str]):

    @staticmethod
    def from_yaml(values: dict):
        return Stages(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass(frozen=True)
class Dependencies(StageSpecificProperty[set[str]]):

    def set_for_stage(self, stage: Stage) -> set[str]:
        deps_for_stage = self.for_stage(stage)
        return deps_for_stage if deps_for_stage else set()

    @staticmethod
    def from_yaml(values: dict):
        return Dependencies(build=set(values.get('build', [])), test=set(values.get('test', [])),
                            deploy=set(values.get('deploy', [])), postdeploy=set(values.get('postdeploy', [])))


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
    values: dict

    def to_probe(self, defaults: dict, target: Target) -> V1Probe:
        defaults.update(self.values)
        probe: V1Probe = ApiClient()._ApiClient__deserialize(defaults, V1Probe)
        path = self.path.get_value(target)
        probe.http_get = '/health' if path is None else path
        return probe

    @staticmethod
    def from_yaml(values: dict):
        path = values['path']
        return Probe(path=TargetSpecificProperty.from_yaml(path), values=values)


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
    startupProbe: Optional[Probe]
    livenessProbe: Optional[Probe]
    metrics: Optional[Metrics]

    @staticmethod
    def from_yaml(values: dict):
        mappings = values.get('portMappings')
        startup_probe = values.get('startupProbe')
        liveness_probe = values.get('livenessProbe')
        metrics = values.get('metrics')
        return Kubernetes(portMappings=mappings if mappings else {},
                          startupProbe=Probe.from_yaml(startup_probe) if startup_probe else None,
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
    namespace: Optional[str]
    properties: Properties
    kubernetes: Optional[Kubernetes]
    traefik: Optional[Traefik]

    @staticmethod
    def from_yaml(values: dict):
        props = values.get('properties')
        kubernetes = values.get('kubernetes')
        traefik = values.get('traefik')
        return Deployment(namespace=values.get('namespace'), properties=Properties.from_yaml(props) if props else None,
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

    def __lt__(self, other):
        return self.path < other.path

    def __eq__(self, other):
        return self.path == other.path

    def __hash__(self):
        return hash(self.path)

    @property
    def kubernetes(self) -> Kubernetes:
        if self.deployment is None or self.deployment.kubernetes is None:
            raise AttributeError(f"Project {self.name} does not have kubernetes configuration")
        return self.deployment.kubernetes

    @staticmethod
    def project_yaml_path() -> str:
        return 'deployment/project.yml'

    @property
    def root_path(self) -> str:
        return self.path.replace(Project.project_yaml_path(), '')

    @property
    def deployment_path(self) -> str:
        return str(Path(self.root_path, 'deployment'))

    @property
    def target_path(self) -> str:
        return str(Path(self.deployment_path, '.mpl'))

    @staticmethod
    def from_yaml(values: dict, project_path: str):
        deployment = values.get('deployment')
        dependencies = values.get('dependencies')
        return Project(name=values['name'], description=values['description'], path=project_path,
                       stages=Stages.from_yaml(values.get('stages', {})), maintainer=values.get('maintainer', []),
                       deployment=Deployment.from_yaml(deployment) if deployment else None,
                       dependencies=Dependencies.from_yaml(dependencies) if dependencies else None)


def load_project(root_dir, project_path: str, strict: bool = True) -> Project:
    with open(f'{root_dir}/{project_path}') as f:
        try:
            yaml = YAML()
            yaml_values = yaml.load(f)
            template = pkgutil.get_data(__name__, "schema/project.schema.json")
            if strict and template:
                schema = json.loads(template.decode('utf-8'))
                jsonschema.validate(yaml_values, schema)

            return Project.from_yaml(yaml_values, project_path)
        except jsonschema.exceptions.ValidationError as e:
            logging.warning(f'{project_path} does not comply with schema: {e.message}')
            raise
        except TypeError as e:
            import traceback
            traceback.print_exc()
            logging.warning(f'Type error', e)
            raise
        except Exception as e:
            logging.warning(f'Failed to load {project_path}', e)
            raise
