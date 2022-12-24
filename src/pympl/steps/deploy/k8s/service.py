from typing import Dict, Optional

from kubernetes.client import V1Deployment, V1Container, V1DeploymentSpec, V1PodTemplateSpec, V1ObjectMeta, V1PodSpec, \
    V1DeploymentStrategy, V1RollingUpdateDeployment, V1LabelSelector, V1ContainerPort, V1EnvVar, V1Ingress, \
    V1IngressSpec, V1IngressRule, V1Service, V1ServiceSpec, V1ServicePort, V1ServiceAccount, V1LocalObjectReference, \
    V1EnvVarSource, V1SecretKeySelector
from ruamel.yaml import YAML

from .resources import to_yaml, V1SealedSecret
from ...models import Input
from ....project import Project, KeyValueProperty
from ....target import Target

yaml = YAML()


class ServiceChart:
    step_input: Input
    project: Project
    mappings: dict[int, int]
    env: list[KeyValueProperty]
    sealed_secrets: list[KeyValueProperty]
    target: Target
    release_name: str

    def __init__(self, step_input: Input):
        self.step_input = step_input
        project = self.step_input.project
        self.project = project
        deployment = project.deployment
        self.env = deployment.properties.env if deployment and deployment.properties.env else []
        self.sealed_secrets = deployment.properties.sealedSecret if deployment and deployment.properties.sealedSecret else []
        self.mappings = self.project.kubernetes.portMappings
        self.target = step_input.build_properties.target
        self.release_name = self.project.name.lower()

    def _to_labels(self) -> Dict:
        build_properties = self.step_input.build_properties
        # TODO: extract version from build properties
        app_labels = {'name': self.project.name, 'app.kubernetes.io/version': 'pr-1234',
                      'app.kubernetes.io/managed-by': 'Helm', 'app.kubernetes.io/name': self.release_name,
                      'app.kubernetes.io/instance': self.release_name}

        if len(self.project.maintainer) > 0:
            app_labels['maintainers'] = ".".join(self.project.maintainer).replace(' ', '_')
            app_labels["maintainer"] = self.project.maintainer[0].replace(' ', '_')

        if build_properties.git.tag:
            app_labels['version'] = build_properties.git.tag
        elif build_properties.git.pr_number:
            app_labels['version'] = build_properties.git.pr_number

        if build_properties.git.revision:
            app_labels['revision'] = build_properties.git.revision

        return app_labels

    def _to_annotations(self) -> Dict:
        return {'description': self.project.description}

    def _to_object_meta(self):
        return V1ObjectMeta(name=self.project.name, labels=self._to_labels())

    def _to_selector(self):
        return V1LabelSelector(match_labels={"app.kubernetes.io/instance": self.release_name,
                                             "app.kubernetes.io/name": self.release_name})

    def to_service(self) -> V1Service:
        service_ports = list(map(lambda key: V1ServicePort(port=key, target_port=self.mappings[key], protocol="TCP",
                                                           name=f"{key}-webservice-port"), self.mappings.keys()))

        return V1Service(api_version='v1', kind='Service', metadata=self._to_object_meta(),
                         spec=V1ServiceSpec(type="ClusterIP", ports=service_ports,
                                            selector=self._to_selector().match_labels))

    def to_ingress(self) -> V1Ingress:
        return V1Ingress(metadata=self._to_object_meta(), spec=V1IngressSpec(rules=[V1IngressRule()]))

    def to_service_account(self) -> V1ServiceAccount:
        return V1ServiceAccount(api_version="v1", kind="ServiceAccount", metadata=self._to_object_meta(),
                                image_pull_secrets=[V1LocalObjectReference("bigdataregistry")])

    def to_chart(self) -> dict[str, str]:
        chart = {'deployment': to_yaml(self.to_deployment()), 'serviceaccount': to_yaml(self.to_service_account()),
                 'service': to_yaml(self.to_service())}
        if self.sealed_secrets:
            chart['sealedsecrets'] = to_yaml(self.to_sealed_secrets())
        return chart

    def to_sealed_secrets(self) -> Optional[V1SealedSecret]:
        if self.sealed_secrets is None:
            return None

        secrets: dict[str, str] = {}
        for secret in self.sealed_secrets:
            secrets[secret.key] = secret.get_value(self.target)

        return V1SealedSecret(name=self.release_name, secrets=secrets)

    def to_deployment(self) -> V1Deployment:
        deployment = self.project.deployment
        if deployment is None:
            raise AttributeError("deployment field should be set")

        kubernetes = deployment.kubernetes
        if kubernetes is None:
            raise AttributeError("deployment.kubernetes field should be set")

        ports = list(map(lambda key: V1ContainerPort(container_port=key, host_port=self.mappings[key], protocol="TCP"),
                         self.mappings.keys()))
        env_vars = list(
            filter(lambda v: v.value, map(lambda e: V1EnvVar(name=e.key, value=e.get_value(self.target)), self.env)))

        sealed_for_target = list(
            filter(lambda v: v.get_value(self.target) is not None, deployment.properties.sealedSecret))
        sealed_secrets = list(map(lambda e: V1EnvVar(name=e.key, value_from=V1EnvVarSource(
            secret_key_ref=V1SecretKeySelector(key=e.key, name=self.release_name, optional=False))),
                                  sealed_for_target))

        startup_probe_defaults = {
            'initialDelaySeconds': 4,  # 0 - We expect service to rarely be up within 4 secs.
            'periodSeconds': 2,  # 10 - We want the service to become available as soon as possible
            'timeoutSeconds': 3,  # 1 - If the app is very busy during the startup stage, 1 second might be too fast
            'successThreshold': 1,  # 1 - We want the service to become available as soon as possible
            'failureThreshold': 60  # 3 - 4 + 60 * 2 = more than 2 minutes
        }

        liveness_probe_defaults = {
            'periodSeconds': 30,  # 10
            'timeoutSeconds': 20,  # 1 - Busy apps may momentarily have long timeouts
            'successThreshold': 1,  # 1
            'failureThreshold': 3  # 3
        }

        container = V1Container(
            name=self.project.name,
            image=self.step_input.docker_image_tag(),
            env=env_vars + sealed_secrets,
            ports=ports,
            image_pull_policy="Always",
            liveness_probe=kubernetes.livenessProbe.to_probe(liveness_probe_defaults,
                                                             self.target) if kubernetes.livenessProbe else None,
            startup_probe=kubernetes.startupProbe.to_probe(startup_probe_defaults,
                                                           self.target) if kubernetes.startupProbe else None
        )

        return V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=V1ObjectMeta(annotations=self._to_annotations(), name=self.release_name,
                                  labels=self._to_labels()),
            spec=V1DeploymentSpec(
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
