import logging
import pkgutil
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar, Dict, Any

import jsonschema
from mypy.checker import Generic
from ruamel.yaml import YAML

from .stage import Stage
from .target import Target

T = TypeVar('T')


@dataclass(frozen=True)
class TargetSpecificProperty(Generic[T]):
    pr: Optional[T]  # pylint: disable=invalid-name
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
        return None

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
        return list(map(KeyValueProperty.from_yaml, values))


@dataclass(frozen=True)
class Properties:
    env: list[KeyValueProperty]
    sealed_secret: list[KeyValueProperty]

    @staticmethod
    def from_yaml(values: Dict[Any, Any]):
        return Properties(env=list(map(KeyValueProperty.from_yaml, values.get('env', []))),
                          sealed_secret=list(
                              map(KeyValueProperty.from_yaml, values.get('sealedSecret', []))))


@dataclass(frozen=True)
class Probe:
    path: TargetSpecificProperty[str]
    values: dict

    STARTUP_PROBE_DEFAULTS = {
        'initialDelaySeconds': 4,  # 0 - We expect service to rarely be up within 4 secs.
        'periodSeconds': 2,  # 10 - We want the service to become available as soon as possible
        'timeoutSeconds': 3,  # 1 - If the app is very busy during the startup stage, 1 second might be too fast
        'successThreshold': 1,  # 1 - We want the service to become available as soon as possible
        'failureThreshold': 60  # 3 - 4 + 60 * 2 = more than 2 minutes
    }

    LIVENESS_PROBE_DEFAULTS = {
        'periodSeconds': 30,  # 10
        'timeoutSeconds': 20,  # 1 - Busy apps may momentarily have long timeouts
        'successThreshold': 1,  # 1
        'failureThreshold': 3  # 3
    }

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
    port_mappings: dict[int, int]
    liveness_probe: Optional[Probe]
    startup_probe: Optional[Probe]
    metrics: Optional[Metrics]

    @staticmethod
    def from_yaml(values: dict):
        mappings = values.get('portMappings')
        liveness_probe = values.get('livenessProbe')
        startup_probe = values.get('startupProbe')
        metrics = values.get('metrics')
        return Kubernetes(port_mappings=mappings if mappings else {},
                          liveness_probe=Probe.from_yaml(liveness_probe) if liveness_probe else None,
                          startup_probe=Probe.from_yaml(startup_probe) if startup_probe else None,
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
        return Traefik(hosts=(list(map(Host.from_yaml, hosts) if hosts else [])))


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
            raise AttributeError(f"Project '{self.name}' does not have kubernetes configuration")
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
    with open(f'{root_dir}/{project_path}', encoding='utf-8') as file:
        try:
            yaml = YAML()
            yaml_values = yaml.load(file)
            template = pkgutil.get_data(__name__, "schema/project.schema.yml")
            if strict and template:
                schema = yaml.load(template.decode('utf-8'))
                jsonschema.validate(yaml_values, schema)

            return Project.from_yaml(yaml_values, project_path)
        except jsonschema.exceptions.ValidationError as exc:
            logging.warning(f'{project_path} does not comply with schema: {exc.message}')
            raise
        except TypeError:
            traceback.print_exc()
            logging.warning('Type error', exc_info=True)
            raise
        except Exception:
            logging.warning(f'Failed to load {project_path}', exc_info=True)
            raise
