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
from typing import Optional, TypeVar, Any, List

import jsonschema
from mypy.checker import Generic
from ruamel.yaml import YAML

from .constants import RUN_ARTIFACTS_FOLDER
from .validation import validate

T = TypeVar("T")


def without_keys(dictionary: dict, keys: set[str]):
    return {k: dictionary[k] for k in dictionary.keys() - keys}


@dataclass(frozen=True)
class Target(Enum):
    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return str(self.value)

    PULL_REQUEST = "PullRequest"
    PULL_REQUEST_BASE = "PullRequestBase"
    ACCEPTANCE = "Acceptance"
    PRODUCTION = "Production"


@dataclass(frozen=True)
class Stage:
    name: str
    icon: str


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
        return TargetProperty(
            pr=values.get("pr"),
            test=values.get("test"),
            acceptance=values.get("acceptance"),
            production=values.get("production"),
            all=values.get("all"),
        )


@dataclass(frozen=True)
class KeyValueProperty(TargetProperty[str]):
    key: str

    @staticmethod
    def from_config(values: dict):
        return KeyValueProperty(
            key=values["key"],
            pr=values.get("pr"),
            test=values.get("test"),
            acceptance=values.get("acceptance"),
            production=values.get("production"),
            all=values.get("all"),
        )


@dataclass(frozen=True)
class KeyValueRef:
    key: str
    value_from: dict

    @staticmethod
    def from_config(values: dict):
        key = values["key"]
        value_from = values["valueFrom"]

        return KeyValueRef(
            key=key,
            value_from=value_from,
        )


@dataclass(frozen=True)
class EnvCredential:
    key: str
    secret_id: str

    @staticmethod
    def from_config(values: dict):
        key = values.get("key")
        secret_id = values.get("id")
        if not key or not secret_id:
            raise KeyError("Credential must have a key and id set.")
        return EnvCredential(key, secret_id)


@dataclass(frozen=True)
class StageSpecificProperty(Generic[T]):
    stages: dict[str, Optional[T]]

    def for_stage(self, stage: str) -> Optional[T]:
        if stage not in self.stages.keys():
            return None
        return self.stages[stage]


@dataclass(frozen=True)
class Stages(StageSpecificProperty[str]):
    def all(self) -> dict[str, Optional[str]]:
        return self.stages

    @staticmethod
    def from_config(values: dict):
        return Stages(values)


@dataclass(frozen=True)
class Dependencies(StageSpecificProperty[set[str]]):
    def set_for_stage(self, stage: str) -> set[str]:
        deps_for_stage = self.for_stage(stage)
        return deps_for_stage if deps_for_stage else set()

    def all(self) -> dict[str, set[str]]:
        return {key: self.set_for_stage(key) for key in self.stages.keys()}

    @staticmethod
    def from_config(values: dict):
        return Dependencies(values)


@dataclass(frozen=True)
class Env:
    @staticmethod
    def from_config(values: list[dict]):
        return list(map(KeyValueProperty.from_config, values))


@dataclass(frozen=True)
class Properties:
    env: list[KeyValueProperty]
    sealed_secret: list[KeyValueProperty]
    kubernetes: list[KeyValueRef]

    @staticmethod
    def from_config(values: dict[Any, Any]):
        return Properties(
            env=list(map(KeyValueProperty.from_config, values.get("env", []))),
            sealed_secret=list(
                map(KeyValueProperty.from_config, values.get("sealedSecret", []))
            ),
            kubernetes=list(map(KeyValueRef.from_config, values.get("kubernetes", []))),
        )


@dataclass(frozen=True)
class Probe:
    path: TargetProperty[str]
    values: dict

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Probe(path=TargetProperty.from_config(values["path"]), values=values)


@dataclass(frozen=True)
class Alert:
    name: str
    expr: str
    for_duration: str
    description: str
    severity: str

    @staticmethod
    def from_config(values: dict):
        name = values.get("name")
        expr = values.get("expr")
        for_duration = values.get("forDuration")
        description = values.get("description")
        severity = values.get("severity")
        if not name or not expr or not for_duration or not description or not severity:
            raise KeyError(
                "Alerts must have a name, expr, forDuration, description and severity set."
            )
        return Alert(name, expr, for_duration, description, severity)


@dataclass(frozen=True)
class Metrics:
    path: str
    port: Optional[str]
    enabled: bool
    alerts: list[Alert]

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Metrics(
            path=values.get("path", "/metrics"),
            port=values.get("port", None),
            enabled=values.get("enabled", False),
            alerts=[Alert.from_config(v) for v in values.get("alerts", [])],
        )


@dataclass(frozen=True)
class ResourceSpecification:
    cpus: Optional[TargetProperty[float]]
    mem: Optional[TargetProperty[int]]
    disk: Optional[TargetProperty[int]]

    @staticmethod
    def from_config(values: dict):
        return ResourceSpecification(
            cpus=TargetProperty.from_config(values.get("cpus", {})),
            mem=TargetProperty.from_config(values.get("mem", {})),
            disk=TargetProperty.from_config(values.get("disk", {})),
        )


@dataclass(frozen=True)
class Resources:
    instances: Optional[TargetProperty[int]]
    limit: Optional[ResourceSpecification]
    request: Optional[ResourceSpecification]

    @staticmethod
    def from_config(values: dict):
        return Resources(
            instances=TargetProperty.from_config(values.get("instances", {})),
            limit=ResourceSpecification.from_config(values.get("limit", {})),
            request=ResourceSpecification.from_config(values.get("request", {})),
        )


@dataclass(frozen=True)
class Job:
    cron: TargetProperty[dict]
    job: dict
    spark: dict

    @staticmethod
    def from_config(values: dict):
        if not values:
            return None
        return Job(
            cron=TargetProperty.from_config(values.get("cron", {})),
            job=without_keys(values, {"cron"}),
            spark=values.get("spark", {}),
        )


@dataclass(frozen=True)
class Rancher:
    project_id: TargetProperty[dict]

    @staticmethod
    def from_config(values: dict):
        return Rancher(
            project_id=TargetProperty.from_config(values.get("projectId", {}))
        )


@dataclass(frozen=True)
class Kubernetes:
    rancher: Optional[Rancher]
    port_mappings: dict[int, int]
    liveness_probe: Optional[Probe]
    startup_probe: Optional[Probe]
    metrics: Optional[Metrics]
    resources: Resources
    job: Optional[Job]
    image_pull_secrets: dict
    role: Optional[dict]
    command: Optional[TargetProperty[str]]
    args: Optional[TargetProperty[str]]
    labels: Optional[list[KeyValueProperty]]
    deployment_strategy: Optional[dict]

    @staticmethod
    def from_config(values: dict):
        return Kubernetes(
            rancher=Rancher.from_config(values.get("rancher", {})),
            port_mappings=values.get("portMappings", {}),
            liveness_probe=Probe.from_config(values.get("livenessProbe", {})),
            startup_probe=Probe.from_config(values.get("startupProbe", {})),
            metrics=Metrics.from_config(values.get("metrics", {})),
            resources=Resources.from_config(values.get("resources", {})),
            job=Job.from_config(values.get("job", {})),
            image_pull_secrets=values.get("imagePullSecrets", {}),
            role=values.get("role"),
            command=TargetProperty.from_config(values.get("command", {})),
            args=TargetProperty.from_config(values.get("args", {})),
            labels=list(map(KeyValueProperty.from_config, values.get("labels", []))),
            deployment_strategy=values.get("deploymentStrategy", {}),
        )


@dataclass(frozen=True)
class TraefikAdditionalRoute:
    name: str
    middlewares: list[str]
    entrypoints: list[str]

    @staticmethod
    def from_config(values: Optional[dict]):
        if not values:
            return None
        return TraefikAdditionalRoute(
            name=values.get("name", {}),
            middlewares=values.get("middlewares", {}),
            entrypoints=values.get("entrypoints", {}),
        )


@dataclass(frozen=True)
class TraefikHost:
    host: TargetProperty[str]
    service_port: Optional[int]
    has_swagger: bool
    tls: Optional[TargetProperty[str]]
    whitelists: TargetProperty[list[str]]
    priority: Optional[TargetProperty[int]]
    insecure: bool
    additional_route: Optional[str]

    @staticmethod
    def from_config(values: dict):
        return TraefikHost(
            host=TargetProperty.from_config(values.get("host", {})),
            service_port=values.get("servicePort"),
            has_swagger=values.get("hasSwagger", True),
            tls=TargetProperty.from_config(values.get("tls", {})),
            whitelists=TargetProperty.from_config(values.get("whitelists", {})),
            priority=TargetProperty.from_config(values.get("priority", {})),
            insecure=values.get("insecure", False),
            additional_route=values.get("additionalRoute", None),
        )


@dataclass
class DagsterSecret:
    name: str

    @staticmethod
    def from_config(values: dict):
        return DagsterSecret(name=values.get("name", ""))


@dataclass(frozen=True)
class Dagster:
    repo: str
    secrets: List[DagsterSecret]

    @staticmethod
    def from_config(values: dict):
        return Dagster(
            repo=values.get("repo", ""),
            secrets=[DagsterSecret.from_config(v) for v in values.get("secrets", [])],
        )


@dataclass(frozen=True)
class Traefik:
    hosts: list[TraefikHost]

    @staticmethod
    def from_config(values: dict):
        hosts = values.get("hosts")
        return Traefik(
            hosts=(list(map(TraefikHost.from_config, hosts) if hosts else [])),
        )


@dataclass(frozen=True)
class BPM:
    project_id: str

    @staticmethod
    def from_config(values: dict):
        return BPM(
            project_id=values.get("projectId", ""),
        )


@dataclass(frozen=True)
class Docker:
    host_name: str

    @staticmethod
    def from_config(values: dict):
        return Docker(host_name=values["hostName"])


@dataclass(frozen=True)
class BuildArgs:
    plain: list[KeyValueProperty]
    credentials: list[EnvCredential]

    @staticmethod
    def from_config(values: dict):
        return BuildArgs(
            plain=list(map(KeyValueProperty.from_config, values.get("plain", []))),
            credentials=list(
                map(EnvCredential.from_config, values.get("credentials", []))
            ),
        )


@dataclass(frozen=True)
class Build:
    args: BuildArgs

    @staticmethod
    def from_config(values: dict):
        return Build(args=BuildArgs.from_config(values.get("args", {})))


@dataclass(frozen=True)
class Deployment:
    cluster: Optional[TargetProperty[str]]
    namespace: Optional[str]
    properties: Optional[Properties]
    kubernetes: Optional[Kubernetes]
    dagster: Optional[Dagster]
    traefik: Optional[Traefik]
    bpm: Optional[BPM]

    @staticmethod
    def from_config(values: dict):
        props = values.get("properties")
        kubernetes = values.get("kubernetes")
        dagster = values.get("dagster")
        traefik = values.get("traefik")
        bpm = values.get("bpm")
        cluster = values.get("cluster")

        return Deployment(
            cluster=TargetProperty.from_config(cluster) if cluster else None,
            namespace=values.get("namespace"),
            properties=Properties.from_config(props) if props else None,
            kubernetes=Kubernetes.from_config(kubernetes) if kubernetes else None,
            dagster=Dagster.from_config(dagster) if dagster else None,
            traefik=Traefik.from_config(traefik) if traefik else None,
            bpm=BPM.from_config(bpm) if bpm else None,
        )


@dataclass(frozen=True)
class ProjectName:
    name: str
    namespace: Optional[str]


@dataclass(frozen=True)
class Project:
    name: str
    description: str
    path: str
    pipeline: Optional[str]
    stages: Stages
    maintainer: list[str]
    docker: Optional[Docker]
    build: Optional[Build]
    deployment: Optional[Deployment]
    dependencies: Optional[Dependencies]

    OVERRIDE_TOKEN = "-override-"

    def __lt__(self, other):
        return self.path < other.path

    def __eq__(self, other):
        return self.path == other.path

    def __hash__(self):
        return hash(self.path)

    @property
    def to_name(self) -> ProjectName:
        return ProjectName(
            name=self.name,
            namespace=(
                self.deployment.namespace
                if self.deployment and self.deployment.namespace
                else None
            ),
        )

    @property
    def kubernetes(self) -> Kubernetes:
        if self.deployment is None or self.deployment.kubernetes is None:
            raise KeyError(
                f"Project '{self.name}' does not have kubernetes configuration"
            )
        return self.deployment.kubernetes

    @property
    def dagster(self) -> Dagster:
        if self.deployment is None or self.deployment.dagster is None:
            raise KeyError(f"Project '{self.name}' does not have dagster configuration")
        return self.deployment.dagster

    @property
    def bpm(self) -> BPM:
        if self.deployment is None or self.deployment.bpm is None:
            raise KeyError(f"Project '{self.name}' does not have bpm configuration")
        return self.deployment.bpm

    @property
    def resources(self) -> Resources:
        return self.kubernetes.resources

    @property
    def job(self) -> Job:
        if self.kubernetes.job is None:
            raise KeyError(
                f"Project '{self.name}' does not have kubernetes.job configuration"
            )
        return self.kubernetes.job

    @property
    def project_yaml_file_name(self) -> str:
        return Path(self.path).name

    @staticmethod
    def to_override_pattern(project_path: str) -> str:
        suffix = Path(project_path).suffix
        return project_path.replace(suffix, Project.OVERRIDE_TOKEN + f"*{suffix}")

    @staticmethod
    def to_parent_project_name(project_path: Path) -> Path:
        return project_path.parent / (
            project_path.stem.split(Project.OVERRIDE_TOKEN)[0] + project_path.suffix
        )

    @property
    def root_path(self) -> Path:
        return Path(self.path).parent.parent

    @property
    def deployment_path(self) -> Path:
        return Path(self.path).parent

    @property
    def target_path(self) -> Path:
        return self.deployment_path / RUN_ARTIFACTS_FOLDER

    @property
    def test_containers_path(self) -> Path:
        return self.deployment_path / "docker-compose-test.yml"

    @property
    def test_report_path(self) -> Path:
        return Path(self.root_path) / "target/test-reports"

    @staticmethod
    def from_config(values: dict, project_path: Path):
        docker_config = values.get("docker")
        deployment = values.get("deployment")
        dependencies = values.get("dependencies")
        return Project(
            name=values["name"],
            description=values["description"],
            path=str(project_path),
            pipeline=values.get("pipeline"),
            stages=Stages.from_config(values.get("stages", {})),
            maintainer=values.get("maintainer", []),
            docker=Docker.from_config(docker_config) if docker_config else None,
            build=Build.from_config(values.get("build", {})),
            deployment=Deployment.from_config(deployment) if deployment else None,
            dependencies=(
                Dependencies.from_config(dependencies) if dependencies else None
            ),
        )


def validate_project(yaml_values: dict, root_dir: Path) -> dict:
    """
    :type yaml_values: the yaml dictionary to validate
    :type root_dir: the root dir
    :return: the validated schema
    :raises `jsonschema.exceptions.ValidationError` when validation fails
    """
    template = pkgutil.get_data(__name__, "schema/project.schema.yml")
    if not template:
        raise ValueError("Schema project.schema.yml not found in package")
    validate(yaml_values, template.decode("utf-8"), root_dir)

    return yaml_values


def load_possible_parent(
    full_path: Path,
    loader: YAML,
) -> Optional[dict]:
    if Project.OVERRIDE_TOKEN not in str(full_path):
        return None
    parent_project_path = Project.to_parent_project_name(full_path)
    with open(parent_project_path, encoding="utf-8") as file:
        return loader.load(file)


def load_project(
    root_dir: Path,
    project_path: Path,
    strict: bool = True,
    log: bool = True,
    safe: bool = False,
) -> Project:
    """
    Load a `project.yml` to `Project` data class
    :param root_dir: is the root of the project path. It contains the mpyl_config.yml and run_properties.yml files
    :param project_path: relative path from `root_dir` to the `project.yml`
    :param strict: indicates whether the schema should be validated
    :param log: indicates whether problems should be logged as warning
    :param safe: indicates that correctness should be prioritized over speed. Safe loading is important
    when the values possibly end up in artifacts
    :return: `Project` data class
    """
    log_level = logging.WARNING if log else logging.DEBUG
    full_path = root_dir / project_path
    with open(full_path, encoding="utf-8") as file:
        try:
            start = time.time()
            loader: YAML = YAML(typ=None if safe else "unsafe")
            yaml_values: dict = loader.load(file)
            parent_yaml_values: Optional[dict] = load_possible_parent(full_path, loader)
            yaml_values = merge_dicts(yaml_values, parent_yaml_values, True)
            if strict:
                validate_project(yaml_values, root_dir=root_dir)
            project = Project.from_config(yaml_values, project_path)
            logging.debug(
                f"Loaded project {project.path} in {(time.time() - start) * 1000} ms"
            )
            return project
        except jsonschema.exceptions.ValidationError as exc:
            logging.log(
                log_level, f"{project_path} does not comply with schema: {exc.message}"
            )
            raise
        except TypeError:
            traceback.print_exc()
            logging.log(log_level, "Type error", exc_info=True)
            raise
        except Exception:
            logging.log(log_level, f"Failed to load {project_path}", exc_info=True)
            raise


def merge_dicts(
    yaml_values: dict, parent_yaml_values: Optional[dict], root_level=False
) -> dict:
    """
    Merge yml values and possible parent yaml values. YML values take precedence over parent values.
    stages are not merged, but overridden.
    :param root_level: The current level is the root level, false for nested levels
    :param yaml_values: the original yml values
    :param parent_yaml_values: the possible parent, if None, the original values are returned
    :return: the merged values.
    """
    if parent_yaml_values is None:
        return yaml_values
    merged = parent_yaml_values.copy()
    for key, value in yaml_values.items():
        # ignore all keys that are not allowed to be overridden
        if root_level and key not in ("stages", "deployment", "name", "description"):
            continue
        # overriden project does not inherit stages
        if root_level and key == "stages":
            merged[key] = value
        elif (
            key in merged and isinstance(merged[key], dict) and isinstance(value, dict)
        ):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_env_variables(project: Project, target: Target) -> dict[str, str]:
    if project.deployment is None or project.deployment.properties is None:
        raise KeyError(
            f"No deployment information was found for project: {project.name}"
        )
    if len(project.deployment.properties.env) == 0:
        raise KeyError(f"No properties.env is defined for project: {project.name}")

    env_variables: dict[str, str] = {
        env_variable.key: env_variable.get_value(target)
        for env_variable in project.deployment.properties.env
    }

    return env_variables
