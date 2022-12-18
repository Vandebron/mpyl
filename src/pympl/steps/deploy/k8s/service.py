from io import StringIO
from typing import Dict

from kubernetes.client import V1Deployment, V1Container, V1DeploymentSpec, V1PodTemplateSpec, V1ObjectMeta, V1PodSpec, \
    V1DeploymentStrategy, V1RollingUpdateDeployment, V1LabelSelector, V1ContainerPort, V1EnvVar, V1Ingress, \
    V1IngressSpec, V1IngressRule, V1Service, V1ServiceSpec, V1ServicePort, V1Probe
from ruamel.yaml import YAML

from ...models import Input
from ....project import Project
from ....target import Target

yaml = YAML()


def camel_case(text):
    return ''.join(word.title() if i else word for i, word in enumerate(text.split('_')))


def to_yaml(resource: object) -> str:
    def remove_none(obj):
        if isinstance(obj, (list, tuple, set)):
            return type(obj)(remove_none(x) for x in obj if x is not None)
        elif isinstance(obj, dict):
            return type(obj)((remove_none(camel_case(k)), remove_none(v))
                             for k, v in obj.items() if k is not None and v is not None)
        else:
            return obj

    resource_dict = resource.to_dict() if hasattr(resource, "to_dict") else {}
    stream = StringIO()
    yaml.dump(remove_none(resource_dict), stream)
    return stream.getvalue()


class ServiceDeployment:
    step_input: Input
    project: Project
    mappings: dict[int, int]
    target: Target

    def __init__(self, step_input: Input):
        self.step_input = step_input
        self.project = self.step_input.project
        self.mappings = self.project.kubernetes.portMappings
        self.target = step_input.build_properties.target

    def _get_labels(self) -> Dict:
        build_properties = self.step_input.build_properties
        app_labels = {"name": self.project.name}

        if len(self.project.maintainer) > 0:
            app_labels["maintainers"] = ".".join(self.project.maintainer).replace(' ', '_')
            app_labels["maintainer"] = self.project.maintainer[0].replace(' ', '_')

        if build_properties.git.tag:
            app_labels["version"] = build_properties.git.tag
        elif build_properties.git.pr_number:
            app_labels["version"] = build_properties.git.pr_number

        if build_properties.git.revision:
            app_labels["revision"] = build_properties.git.revision

        return app_labels

    def _get_annotations(self) -> Dict:
        return {'description': self.project.description}

    def _to_object_meta(self):
        return V1ObjectMeta(name=self.project.name, labels=self._get_labels())

    def to_service(self) -> V1Service:
        service_ports = list(map(lambda key: V1ServicePort(port=key, target_port=self.mappings[key], protocol="TCP",
                                                           name=f"{key}-webservice-port"), self.mappings.keys()))

        return V1Service(metadata=self._to_object_meta(), spec=V1ServiceSpec(type="ClusterIP", ports=service_ports))

    def to_ingress(self) -> V1Ingress:
        return V1Ingress(metadata=self._to_object_meta(), spec=V1IngressSpec(rules=[V1IngressRule()]))

    def to_chart(self) -> dict[str, str]:
        return {'deployment': to_yaml(self.to_deployment()), 'service': to_yaml(self.to_service()),
                'ingress': to_yaml(self.to_ingress())}

    def to_deployment(self) -> V1Deployment:
        deployment = self.project.deployment
        if deployment is None:
            raise AttributeError("deployment field should be set")

        kubernetes = deployment.kubernetes
        if kubernetes is None:
            raise AttributeError("deployment.kubernetes field should be set")

        ports = list(map(lambda key: V1ContainerPort(container_port=key, host_port=self.mappings[key], protocol="TCP"),
                         self.mappings.keys()))

        env_vars = list(map(lambda e: V1EnvVar(e.key, e.get_value(self.target)), deployment.properties.env))

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
            env=env_vars,
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
            metadata=V1ObjectMeta(annotations=self._get_annotations(), name=self.project.name,
                                  labels=self._get_labels()),
            spec=V1DeploymentSpec(
                template=V1PodTemplateSpec(
                    metadata=self._to_object_meta(),
                    spec=V1PodSpec(containers=[container], service_account=self.project.name,
                                   service_account_name=self.project.name),
                ),
                strategy=V1DeploymentStrategy(
                    rolling_update=V1RollingUpdateDeployment(max_surge="25%", max_unavailable="25%"),
                    type="RollingUpdate"),
                selector=V1LabelSelector(match_labels={"app.kubernetes.io/instance": self.project.name,
                                                       "app.kubernetes.io/name": self.project.name}),
            ),
        )
