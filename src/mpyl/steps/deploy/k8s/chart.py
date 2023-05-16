"""
Data classes for the composition of Custom Resource Definitions.
More info: https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
"""

from dataclasses import dataclass
from typing import Dict, Optional

from kubernetes.client import V1Deployment, V1Container, V1DeploymentSpec, V1ObjectMeta, V1PodSpec, \
    V1RollingUpdateDeployment, V1LabelSelector, V1ContainerPort, V1EnvVar, V1Service, \
    V1ServiceSpec, V1ServicePort, V1ServiceAccount, V1LocalObjectReference, \
    V1EnvVarSource, V1SecretKeySelector, V1Probe, ApiClient, V1HTTPGetAction, V1ResourceRequirements, \
    V1PodTemplateSpec, V1DeploymentStrategy, V1Job, V1JobSpec, V1CronJob, V1CronJobSpec, V1JobTemplateSpec, V1ConfigMap
from ruamel.yaml import YAML

from . import get_namespace
from .resources import CustomResourceDefinition, to_dict  # pylint: disable = no-name-in-module
from .resources.sealed_secret import V1SealedSecret
from .resources.spark import to_spark_body, get_spark_config_map_data, V1SparkApplication
from .resources.traefik import V1AlphaIngressRoute, V1AlphaMiddleware, \
    HostWrapper  # pylint: disable = no-name-in-module
from ...models import Input, ArtifactType
from ....project import Project, KeyValueProperty, Probe, Deployment, TargetProperty, Resources, Target, Kubernetes, \
    Job, Traefik, Host
from ....utilities.ephemeral import get_env_variables

yaml = YAML()

# Determined (unscientifically) to be sensible factors.
# Based on actual CPU usage, pods rarely use more than 10% of the allocated CPU. 60% usage is healthy, so we
# scale down to 20% in order to keep some slack.
# Memory is cheaper, but poses a harder limit (OOM when exceeding limit), so we are more generous than with CPU.
CPU_REQUEST_SCALE_FACTOR = 0.2
MEM_REQUEST_SCALE_FACTOR = 0.5


def try_parse_target(value: object, target: Target):
    if isinstance(value, dict):
        maybe_value = TargetProperty.from_config(value).get_value(target)
        if maybe_value:
            return maybe_value

    return value


def with_target(dictionary: dict, target: Target) -> dict:
    def with_targets_parsed(obj):
        if isinstance(obj, dict):
            return type(obj)((k, try_parse_target(with_targets_parsed(v), target)) for k, v in obj.items())

        return obj

    return with_targets_parsed(dictionary)


@dataclass(frozen=True)
class ResourceDefaults:
    instances: TargetProperty[int]
    cpus: TargetProperty[float]
    mem: TargetProperty[int]

    @staticmethod
    def from_config(resources: dict):
        limit = resources['limit']
        return ResourceDefaults(instances=TargetProperty.from_config(resources['instances']),
                                cpus=TargetProperty.from_config(limit['cpus']),
                                mem=TargetProperty.from_config(limit['mem']))


@dataclass(frozen=True)
class DeploymentDefaults:
    resources_defaults: ResourceDefaults
    liveness_probe_defaults: dict
    startup_probe_defaults: dict
    job_defaults: dict
    treafik_defaults: dict
    white_lists: dict

    @staticmethod
    def from_config(config: dict):
        deployment_values = config.get('project', {}).get('deployment', {})
        if deployment_values is None:
            raise KeyError("Configuration should have project.deployment section")
        kubernetes = deployment_values.get('kubernetes', {})
        return DeploymentDefaults(
            resources_defaults=ResourceDefaults.from_config(kubernetes['resources']),
            liveness_probe_defaults=kubernetes['livenessProbe'],
            startup_probe_defaults=kubernetes['startupProbe'],
            job_defaults=kubernetes.get('job', {}),
            treafik_defaults=deployment_values.get('traefik', {}),
            white_lists=config.get('whiteLists', {})
        )


class ChartBuilder:
    step_input: Input
    project: Project
    mappings: dict[int, int]
    env: list[KeyValueProperty]
    sealed_secrets: list[KeyValueProperty]
    deployment: Deployment
    target: Target
    release_name: str
    config_defaults: DeploymentDefaults

    def __init__(self, step_input: Input):
        self.step_input = step_input
        project = self.step_input.project
        self.project = project
        if project.deployment is None:
            raise AttributeError("deployment field should be set")

        self.config_defaults = DeploymentDefaults.from_config(step_input.run_properties.config)

        self.deployment = project.deployment
        properties = self.deployment.properties
        self.env = properties.env if properties and properties.env else []
        self.sealed_secrets = properties.sealed_secret if properties and properties.sealed_secret else []
        self.mappings = self.project.kubernetes.port_mappings
        self.target = step_input.run_properties.target
        self.release_name = self.project.name.lower()

    def _to_labels(self) -> Dict:
        run_properties = self.step_input.run_properties
        app_labels = {'name': self.release_name, 'app.kubernetes.io/version': run_properties.versioning.identifier,
                      'app.kubernetes.io/managed-by': 'Helm', 'app.kubernetes.io/name': self.release_name,
                      'app.kubernetes.io/instance': self.release_name}

        if len(self.project.maintainer) > 0:
            app_labels['maintainers'] = ".".join(self.project.maintainer).replace(' ', '_')
            app_labels["maintainer"] = self.project.maintainer[0].replace(' ', '_')

        app_labels['version'] = run_properties.versioning.identifier

        if run_properties.versioning.revision:
            app_labels['revision'] = run_properties.versioning.revision

        return app_labels

    def _to_annotations(self) -> Dict:
        return {'description': self.project.description}

    def _to_object_meta(self, name: Optional[str] = None):
        return V1ObjectMeta(name=name if name else self.release_name, labels=self._to_labels())

    def _to_selector(self):
        return V1LabelSelector(match_labels={"app.kubernetes.io/instance": self.release_name,
                                             "app.kubernetes.io/name": self.release_name})

    @staticmethod
    def _to_k8s_model(values: dict, model_type):
        return ApiClient()._ApiClient__deserialize(values, model_type)  # pylint: disable=protected-access

    @staticmethod
    def _to_probe(probe: Probe, defaults: dict, target: Target) -> V1Probe:
        values = defaults.copy()
        values.update(probe.values)
        v1_probe: V1Probe = ChartBuilder._to_k8s_model(values, V1Probe)
        path = probe.path.get_value(target)
        v1_probe.http_get = V1HTTPGetAction(path='/health' if path is None else path, port='port-0')
        return v1_probe

    def to_service(self) -> V1Service:
        service_ports = list(map(lambda key: V1ServicePort(port=key, target_port=self.mappings[key], protocol="TCP",
                                                           name=f"{key}-webservice-port"), self.mappings.keys()))

        return V1Service(api_version='v1', kind='Service', metadata=self._to_object_meta(),
                         spec=V1ServiceSpec(type="ClusterIP", ports=service_ports,
                                            selector=self._to_selector().match_labels))

    def to_job(self) -> V1Job:
        job_container = V1Container(
            name=self.release_name, image=self._get_image(), env=self._get_env_vars(), image_pull_policy="Always",
            resources=self._get_resources()
        )
        pod_template = V1PodTemplateSpec(
            metadata=self._to_object_meta(),
            spec=V1PodSpec(containers=[job_container], service_account=self.release_name,
                           service_account_name=self.release_name, restart_policy="Never")
        )

        defaults = with_target(self.config_defaults.job_defaults, self.target)
        specified = defaults | with_target(self.project.job.job, self.target)

        template_dict = to_dict(pod_template)
        specified['template'] = template_dict
        spec: V1JobSpec = ChartBuilder._to_k8s_model(specified, V1JobSpec)

        return V1Job(api_version='batch/v1', kind='Job', metadata=self._to_object_meta(), spec=spec)

    def to_cron_job(self) -> V1CronJob:
        values = self.project.job.cron
        job_template = V1JobTemplateSpec(spec=self.to_job().spec)
        template_dict = to_dict(job_template)
        values['jobTemplate'] = template_dict
        v1_cron_job_spec: V1CronJobSpec = ChartBuilder._to_k8s_model(values, V1CronJobSpec)
        return V1CronJob(api_version='batch/v1', kind='CronJob', metadata=self._to_object_meta(), spec=v1_cron_job_spec)

    def to_spark_application(self) -> V1SparkApplication:
        return V1SparkApplication(
            schedule=self._get_job().cron['schedule'],
            body=to_spark_body(
                project_name=self.release_name,
                env_vars=get_env_variables(self.project, self.target),
                spark=self._get_job().spark
            ),
        )

    def to_spark_config_map(self) -> V1ConfigMap:
        return V1ConfigMap(
            api_version='v1',
            kind='ConfigMap',
            data=get_spark_config_map_data(),
            metadata=self._to_object_meta()
        )

    def __find_default_port(self) -> int:
        found = next(iter(self.mappings.keys()))
        if found:
            return int(found)
        raise KeyError("No default port found. Did you define a port mapping?")

    def create_host_wrappers(self) -> list[HostWrapper]:
        default_hosts: list[Host] = Traefik.from_config(self.config_defaults.treafik_defaults).hosts

        hosts: list[Host] = self.deployment.traefik.hosts if self.deployment.traefik else []

        first_host = next(iter(hosts), None)
        service_port = first_host.service_port if first_host and first_host.service_port else self.__find_default_port()

        def to_white_list(configured: Optional[TargetProperty[list[str]]]) -> list[str]:
            white_lists = configured.get_value(self.target) if configured else self.config_defaults.white_lists[
                'default']
            addresses = []
            add_dict = dict(
                (address['name'], address['values']) for address in self.config_defaults.white_lists['addresses'])
            for item in white_lists:
                addresses.extend(add_dict[item])

            return addresses

        return [HostWrapper(host=host, name=self.release_name, index=idx, service_port=service_port,
                            white_lists=to_white_list(host.whitelists)) for
                idx, host in enumerate(hosts if hosts else default_hosts)]

    def to_ingress_routes(self) -> V1AlphaIngressRoute:
        hosts = self.create_host_wrappers()

        return V1AlphaIngressRoute(metadata=self._to_object_meta(), hosts=hosts, target=self.target,
                                   pr_number=self.step_input.run_properties.versioning.pr_number)

    def to_middlewares(self) -> dict[str, V1AlphaMiddleware]:
        hosts = self.create_host_wrappers()
        return dict(map(lambda host:
                        (host.full_name,
                         V1AlphaMiddleware(metadata=self._to_object_meta(name=host.full_name),
                                           source_ranges=host.white_lists)),
                        hosts))

    def to_service_account(self) -> V1ServiceAccount:
        return V1ServiceAccount(api_version="v1", kind="ServiceAccount", metadata=self._to_object_meta(),
                                image_pull_secrets=[V1LocalObjectReference("bigdataregistry")])

    def to_sealed_secrets(self) -> V1SealedSecret:
        secrets: dict[str, str] = {}
        for secret in self.sealed_secrets:
            secrets[secret.key] = secret.get_value(self.target)

        return V1SealedSecret(name=self.release_name, secrets=secrets)

    @staticmethod
    def _to_resources(resources: Resources, defaults: ResourceDefaults, target: Target):
        cpus = resources.cpus if resources and resources.cpus else defaults.cpus
        cpus_limit = cpus.get_value(target=target) * 1000.0
        cpus_request = cpus_limit * CPU_REQUEST_SCALE_FACTOR

        mem = resources.mem if resources and resources.mem else defaults.mem
        mem_limit = mem.get_value(target=target)
        mem_request = mem_limit * MEM_REQUEST_SCALE_FACTOR
        return V1ResourceRequirements(limits={'cpu': f'{int(cpus_limit)}m', 'memory': f'{int(mem_limit)}Mi'},
                                      requests={'cpu': f'{int(cpus_request)}m', 'memory': f'{int(mem_request)}Mi'})

    def _get_image(self):
        docker_image = self.step_input.required_artifact
        if not docker_image or docker_image.artifact_type != ArtifactType.DOCKER_IMAGE:
            raise ValueError(
                f'Required artifact of type {ArtifactType.DOCKER_IMAGE.name} must be defined')  # pylint: disable=E1101
        return docker_image.spec['image']

    def _get_resources(self):
        resources = self.project.kubernetes.resources
        defaults = self.config_defaults.resources_defaults
        return ChartBuilder._to_resources(resources, defaults, self.target)

    def _get_kubernetes(self) -> Kubernetes:
        kubernetes = self.deployment.kubernetes
        if kubernetes is None:
            raise AttributeError("deployment.kubernetes field should be set")
        return kubernetes

    def _get_job(self) -> Job:
        job = self._get_kubernetes().job
        if job is None:
            raise AttributeError("deployment.kubernetes.job field should be set")
        return job

    def _get_env_vars(self):

        def _interpolate_namespace(value: Optional[str]) -> Optional[str]:
            if value and '{namespace}' in value:
                namespace = get_namespace(self.step_input.run_properties, self.step_input.project)
                return value.replace('{namespace}', namespace)

            return value

        env_vars = list(
            filter(lambda v: v.value,
                   map(lambda e: V1EnvVar(name=e.key, value=_interpolate_namespace(e.get_value(self.target))),
                       self.env)))

        sealed_for_target = list(
            filter(lambda v: v.get_value(self.target) is not None, self.sealed_secrets))
        sealed_secrets = list(map(lambda e: V1EnvVar(name=e.key, value_from=V1EnvVarSource(
            secret_key_ref=V1SecretKeySelector(key=e.key, name=self.release_name, optional=False))),
                                  sealed_for_target))
        return env_vars + sealed_secrets

    @property
    def is_cron_job(self) -> bool:
        return len(self._get_job().cron.keys()) > 0

    def to_deployment(self) -> V1Deployment:

        ports = [
            V1ContainerPort(container_port=key, host_port=self.mappings[key], protocol="TCP", name=f'port-{idx}')
            for idx, key in enumerate(self.mappings.keys())
        ]

        project = self.project
        resources = project.resources
        kubernetes = project.kubernetes
        defaults = self.config_defaults.resources_defaults

        container = V1Container(
            name=self.release_name,
            image=self._get_image(),
            env=self._get_env_vars(),
            ports=ports,
            image_pull_policy="Always",
            resources=ChartBuilder._to_resources(resources, defaults, self.target),
            liveness_probe=ChartBuilder._to_probe(
                kubernetes.liveness_probe,
                self.config_defaults.liveness_probe_defaults,
                self.target
            ) if kubernetes.liveness_probe else None,
            startup_probe=ChartBuilder._to_probe(
                kubernetes.startup_probe,
                self.config_defaults.startup_probe_defaults,
                self.target)
            if kubernetes.startup_probe else None
        )

        instances = resources.instances if resources.instances else defaults.instances

        return V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=V1ObjectMeta(annotations=self._to_annotations(), name=self.release_name,
                                  labels=self._to_labels()),
            spec=V1DeploymentSpec(
                replicas=instances.get_value(target=self.target),
                template=V1PodTemplateSpec(
                    metadata=self._to_object_meta(),
                    spec=V1PodSpec(containers=[container], service_account=self.release_name,
                                   service_account_name=self.release_name),
                ),
                strategy=V1DeploymentStrategy(
                    rolling_update=V1RollingUpdateDeployment(max_surge="25%", max_unavailable="25%"),
                    type="RollingUpdate"),
                selector=self._to_selector(),
            ),
        )

    def to_common_chart(self) -> dict[str, CustomResourceDefinition]:
        chart = {'service-account': self.to_service_account()}

        if self.sealed_secrets:
            chart['sealed-secrets'] = self.to_sealed_secrets()

        return chart


def to_service_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {
        'deployment': builder.to_deployment(),
        'service': builder.to_service(),
        'ingress-https-route': builder.to_ingress_routes()
    } | builder.to_middlewares()


def to_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {'job': builder.to_job()}


def to_cron_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {'cronjob': builder.to_cron_job()}


def to_spark_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {
        'spark': builder.to_spark_application(),
        'config-map': builder.to_spark_config_map()
    }
