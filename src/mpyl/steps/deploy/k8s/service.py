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
    V1PodTemplateSpec, V1DeploymentStrategy
from ruamel.yaml import YAML

from .resources.crd import to_yaml  # pylint: disable = no-name-in-module
from .resources.customresources import V1AlphaIngressRoute, V1SealedSecret  # pylint: disable = no-name-in-module
from ...models import Input
from ....project import Project, KeyValueProperty, Probe, Deployment, TargetProperty, Resources, Target

yaml = YAML()

# Determined (unscientifically) to be sensible factors.
# Based on actual CPU usage, pods rarely use more than 10% of the allocated CPU. 60% usage is healthy, so we
# scale down to 20% in order to keep some slack.
# Memory is cheaper, but poses a harder limit (OOM when exceeding limit), so we are more generous than with CPU.
CPU_REQUEST_SCALE_FACTOR = 0.2
MEM_REQUEST_SCALE_FACTOR = 0.5


@dataclass(frozen=True)
class ResourceDefaults:
    instances: TargetProperty[int]
    cpus: TargetProperty[float]
    mem: TargetProperty[int]

    @staticmethod
    def from_yaml(resources: dict):
        limit = resources['limit']
        return ResourceDefaults(instances=TargetProperty.from_yaml(resources['instances']),
                                cpus=TargetProperty.from_yaml(limit['cpus']),
                                mem=TargetProperty.from_yaml(limit['mem']))


@dataclass(frozen=True)
class KubernetesConfig:
    resources_defaults: ResourceDefaults
    liveness_probe_defaults: dict
    startup_probe_defaults: dict

    @staticmethod
    def from_yaml(values: dict):
        return KubernetesConfig(resources_defaults=ResourceDefaults.from_yaml(values['resources']),
                                liveness_probe_defaults=values['livenessProbe'],
                                startup_probe_defaults=values['startupProbe'])


class ServiceChart:
    step_input: Input
    project: Project
    mappings: dict[int, int]
    env: list[KeyValueProperty]
    sealed_secrets: list[KeyValueProperty]
    deployment: Deployment
    target: Target
    release_name: str
    image_name: str
    kubernetes_config: KubernetesConfig

    def __init__(self, step_input: Input, image_name: str):
        self.step_input = step_input
        project = self.step_input.project
        self.project = project
        if project.deployment is None:
            raise AttributeError("deployment field should be set")
        kubernetes_config_dict = step_input.run_properties.config.get('project', {}).get('deployment', {}).get(
            'kubernetes', {})
        if kubernetes_config_dict is None:
            raise KeyError("Configuration should have project.deployment.kubernetes section")

        self.kubernetes_config = KubernetesConfig.from_yaml(kubernetes_config_dict)

        self.deployment = project.deployment
        properties = self.deployment.properties
        self.env = properties.env if properties.env else []
        self.sealed_secrets = properties.sealed_secret if properties.sealed_secret else []
        self.mappings = self.project.kubernetes.port_mappings
        self.target = step_input.run_properties.target
        self.release_name = self.project.name.lower()
        self.image_name = image_name

    def _to_labels(self) -> Dict:
        run_properties = self.step_input.run_properties
        app_labels = {'name': self.project.name, 'app.kubernetes.io/version': run_properties.versioning.identifier,
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

    def _to_object_meta(self):
        return V1ObjectMeta(name=self.project.name, labels=self._to_labels())

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
        v1_probe: V1Probe = ServiceChart._to_k8s_model(values, V1Probe)
        path = probe.path.get_value(target)
        v1_probe.http_get = V1HTTPGetAction(path='/health' if path is None else path, port='port-0')
        return v1_probe

    def to_service(self) -> V1Service:
        service_ports = list(map(lambda key: V1ServicePort(port=key, target_port=self.mappings[key], protocol="TCP",
                                                           name=f"{key}-webservice-port"), self.mappings.keys()))

        return V1Service(api_version='v1', kind='Service', metadata=self._to_object_meta(),
                         spec=V1ServiceSpec(type="ClusterIP", ports=service_ports,
                                            selector=self._to_selector().match_labels))

    def to_ingress_routes(self) -> Optional[V1AlphaIngressRoute]:
        if not self.deployment.traefik:
            return None
        return V1AlphaIngressRoute(metadata=self._to_object_meta(), hosts=self.deployment.traefik.hosts,
                                   service_port=123, name=self.release_name, target=self.target)

    def to_service_account(self) -> V1ServiceAccount:
        return V1ServiceAccount(api_version="v1", kind="ServiceAccount", metadata=self._to_object_meta(),
                                image_pull_secrets=[V1LocalObjectReference("bigdataregistry")])

    def to_chart(self) -> dict[str, str]:
        chart = {'deployment': to_yaml(self.to_deployment()), 'serviceaccount': to_yaml(self.to_service_account()),
                 'service': to_yaml(self.to_service())}
        if self.sealed_secrets:
            chart['sealedsecrets'] = to_yaml(self.to_sealed_secrets())

        if self.deployment.traefik:
            chart['ingress-https-route'] = to_yaml(self.to_ingress_routes())

        return chart

    def to_sealed_secrets(self) -> Optional[V1SealedSecret]:
        if self.sealed_secrets is None:
            return None

        secrets: dict[str, str] = {}
        for secret in self.sealed_secrets:
            secrets[secret.key] = secret.get_value(self.target)

        return V1SealedSecret(name=self.release_name, secrets=secrets)

    @staticmethod
    def _to_resources(resources: Resources, defaults: ResourceDefaults, target: Target):
        cpus = resources.cpus if resources.cpus else defaults.cpus
        cpus_limit = cpus.get_value(target=target) * 1000.0
        cpus_request = cpus_limit * CPU_REQUEST_SCALE_FACTOR

        mem = resources.mem if resources.mem else defaults.mem
        mem_limit = mem.get_value(target=target)
        mem_request = mem_limit * MEM_REQUEST_SCALE_FACTOR
        return V1ResourceRequirements(limits={'cpu': f'{int(cpus_limit)}m', 'memory': f'{int(mem_limit)}Mi'},
                                      requests={'cpu': f'{int(cpus_request)}m', 'memory': f'{int(mem_request)}Mi'})

    def to_deployment(self) -> V1Deployment:
        kubernetes = self.deployment.kubernetes
        if kubernetes is None:
            raise AttributeError("deployment.kubernetes field should be set")

        ports = [
            V1ContainerPort(container_port=key, host_port=self.mappings[key], protocol="TCP", name=f'port-{idx}')
            for idx, key in enumerate(self.mappings.keys())
        ]
        env_vars = list(
            filter(lambda v: v.value, map(lambda e: V1EnvVar(name=e.key, value=e.get_value(self.target)), self.env)))

        sealed_for_target = list(
            filter(lambda v: v.get_value(self.target) is not None, self.deployment.properties.sealed_secret))
        sealed_secrets = list(map(lambda e: V1EnvVar(name=e.key, value_from=V1EnvVarSource(
            secret_key_ref=V1SecretKeySelector(key=e.key, name=self.release_name, optional=False))),
                                  sealed_for_target))

        resources = kubernetes.resources
        defaults = self.kubernetes_config.resources_defaults
        instances = resources.instances if resources.instances else defaults.instances

        container = V1Container(
            name=self.project.name,
            image=self.image_name,
            env=env_vars + sealed_secrets,
            ports=ports,
            image_pull_policy="Always",
            resources=ServiceChart._to_resources(resources, defaults, self.target),
            liveness_probe=ServiceChart._to_probe(kubernetes.liveness_probe,
                                                  self.kubernetes_config.liveness_probe_defaults,
                                                  self.target) if kubernetes.liveness_probe else None,
            startup_probe=ServiceChart._to_probe(kubernetes.startup_probe,
                                                 self.kubernetes_config.startup_probe_defaults,
                                                 self.target) if kubernetes.startup_probe else None
        )

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
