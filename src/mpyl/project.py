"""
Datamodel representation of project specific configuration as specified
in the `deployment/project.yml`. It defines how the source code to which it relates
"wants" to be built / tested / deployed.

<details>
  <summary>Schema definition</summary>
```yaml
.. include:: ./schema/project.schema.yml
```
</details>

.. include:: ../../README-dev.md
"""

import logging
import pkgutil
import time
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, TypeVar, Dict, Any, TextIO

import jsonschema
from mypy.checker import Generic
from ruamel.yaml import YAML

from .validation import validate

T = TypeVar('T')


def without_keys(dictionary: dict, keys: set[str]):
    return {k: dictionary[k] for k in dictionary.keys() - keys}


@dataclass(frozen=True)
class Target(Enum):
    def __eq__(self, other):
        return self.value == other.value

    PULL_REQUEST = 'PullRequest'
    PULL_REQUEST_BASE = 'PullRequestBase'
    ACCEPTANCE = 'Acceptance'
    PRODUCTION = 'Production'


@dataclass(frozen=True)
class Stage(Enum):
    def __eq__(self, other):
        return self.value == other.value

    BUILD = 'build'
    TEST = 'test'
    DEPLOY = 'deploy'
    POST_DEPLOY = 'postdeploy'


@dataclass(frozen=True)
class TargetProperty(Generic[T]):
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
    def from_config(values: dict):
        if not values:
            return None
        return TargetProperty(pr=values.get('pr'), test=values.get('test'), acceptance=values.get('acceptance'),
                              production=values.get('production'), all=values.get('all'))


@dataclass(frozen=True)
class KeyValueProperty(TargetProperty[str]):
    key: str

    @staticmethod
    def from_config(values: dict):
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
    def from_config(values: dict):
        return Stages(build=values.get('build'), test=values.get('test'), deploy=values.get('deploy'),
                      postdeploy=values.get('postdeploy'))


@dataclass(frozen=True)
class Dependencies(StageSpecificProperty[set[str]]):

    def set_for_stage(self, stage: Stage) -> set[str]:
        deps_for_stage = self.for_stage(stage)
        return deps_for_stage if deps_for_stage else set()

    @staticmethod
    def from_config(values: dict):
        return Dependencies(build=set(values.get('build', [])), test=set(values.get('test', [])),
                            deploy=set(values.get('deploy', [])), postdeploy=set(values.get('postdeploy', [])))


@dataclass(frozen=True)
class Env:
    @staticmethod
    def from_config(values: list[dict]):
        return list(map(KeyValueProperty.from_config, values))


@dataclass(frozen=True)
class Properties:
    env: list[KeyValueProperty]
    sealed_secret: list[KeyValueProperty]

    @staticmethod
    def from_config(values: Dict[Any, Any]):
        return Properties(env=list(map(KeyValueProperty.from_config, values.get('env', []))),
                          sealed_secret=list(
                              map(KeyValueProperty.from_config, values.get('sealedSecret', []))))


@dataclass(frozen=True)
class Probe:
    path: TargetProperty[str]
    values: dict

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Probe(path=TargetProperty.from_config(values['path']), values=values)


@dataclass(frozen=True)
class Metrics:
    path: str
    enabled: bool

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Metrics(path=values.get('path', '/metrics'), enabled=values.get('enabled', False))


@dataclass(frozen=True)
class Resources:
    instances: Optional[TargetProperty[int]]
    cpus: Optional[TargetProperty[float]]
    mem: Optional[TargetProperty[int]]
    disk: Optional[TargetProperty[int]]

    @staticmethod
    def from_config(values: dict):
        limits = values.get('limit', {})
        return Resources(
            instances=TargetProperty.from_config(limits.get('instances', {})),
            cpus=TargetProperty.from_config(limits.get('cpus', {})),
            mem=TargetProperty.from_config(limits.get('mem', {})),
            disk=TargetProperty.from_config(limits.get('disk', {}))
        )


@dataclass(frozen=True)
class Job:
    cron: dict
    job: dict
    spark: dict

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Job(cron=values.get('cron', {}), job=without_keys(values, {'cron'}), spark=values.get('spark', {}))


@dataclass(frozen=True)
class Kubernetes:
    port_mappings: dict[int, int]
    liveness_probe: Optional[Probe]
    startup_probe: Optional[Probe]
    metrics: Optional[Metrics]
    resources: Resources
    job: Optional[Job]


    @staticmethod
    def from_config(values: dict):
        return Kubernetes(
            port_mappings=values.get('portMappings', {}),
            liveness_probe=Probe.from_config(values.get('livenessProbe', {})),
            startup_probe=Probe.from_config(values.get('startupProbe', {})),
            metrics=Metrics.from_config(values.get('metrics', {})),
            resources=Resources.from_config(values.get('resources', {})),
            job=Job.from_config(values.get('job', {}))
        )


@dataclass(frozen=True)
class Host:
    host: TargetProperty[str]
    tls: TargetProperty[str]
    whitelists: TargetProperty[list[str]]

    @staticmethod
    def from_config(values: dict):
        return Host(
            host=TargetProperty.from_config(values.get('host', {})),
            tls=TargetProperty.from_config(values.get('tls', {})),
            whitelists=TargetProperty.from_config(values.get('whitelists', {}))
        )


@dataclass(frozen=True)
class Traefik:
    hosts: list[Host]

    @staticmethod
    def from_config(values: dict):
        hosts = values.get('hosts')
        return Traefik(hosts=(list(map(Host.from_config, hosts) if hosts else [])))


@dataclass(frozen=True)
class Deployment:
    namespace: Optional[str]
    properties: Properties
    kubernetes: Optional[Kubernetes]
    traefik: Optional[Traefik]

    @staticmethod
    def from_config(values: dict):
        props = values.get('properties')
        kubernetes = values.get('kubernetes')
        traefik = values.get('traefik')
        return Deployment(namespace=values.get('namespace'),
                          properties=Properties.from_config(props) if props else None,
                          kubernetes=Kubernetes.from_config(kubernetes) if kubernetes else None,
                          traefik=Traefik.from_config(traefik) if traefik else None)


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
            raise KeyError(f"Project '{self.name}' does not have kubernetes configuration")
        return self.deployment.kubernetes

    @property
    def resources(self) -> Resources:
        return self.kubernetes.resources

    @property
    def job(self) -> Job:
        if self.kubernetes.job is None:
            raise KeyError(f"Project '{self.name}' does not have kubernetes.job configuration")
        return self.kubernetes.job

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

    @property
    def test_containers_path(self) -> str:
        return str(Path(self.deployment_path, 'docker-compose-test.yml'))

    @property
    def test_report_path(self) -> str:
        return str(Path(self.root_path, 'target/test-reports'))

    @staticmethod
    def from_config(values: dict, project_path: Path):
        deployment = values.get('deployment')
        dependencies = values.get('dependencies')
        return Project(name=values['name'], description=values['description'], path=str(project_path),
                       stages=Stages.from_config(values.get('stages', {})), maintainer=values.get('maintainer', []),
                       deployment=Deployment.from_config(deployment) if deployment else None,
                       dependencies=Dependencies.from_config(dependencies) if dependencies else None)


def validate_project(file: TextIO) -> dict:
    """
    :file the file to validate
    :return: the validated schema
    :raises `jsonschema.exceptions.ValidationError` when validation fails
    """
    yaml_values = YAML(typ='unsafe').load(file)
    template = pkgutil.get_data(__name__, "schema/project.schema.yml")
    if not template:
        raise ValueError('Schema project.schema.yml not found in package')
    validate(yaml_values, template.decode('utf-8'))

    return yaml_values


def load_project(root_dir: Path, project_path: Path, strict: bool = True) -> Project:
    """
    Load a `project.yml` to `Project` data class
    :param root_dir: root source directory
    :param project_path: relative path from `root_dir` to the `project.yml`
    :param strict: indicates whether the schema should be validated
    :return: `Project` data class
    """
    with open(root_dir / project_path, encoding='utf-8') as file:
        try:
            start = time.time()
            yaml_values = validate_project(file) if strict else YAML(typ='unsafe').load(file)
            project = Project.from_config(yaml_values, project_path)
            logging.debug(f'Loaded project {project.path} in {(time.time() - start) * 1000} ms')
            return project
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
