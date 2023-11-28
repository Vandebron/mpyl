"""
Data classes for the composition of Custom Resource Definitions.
More info: https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
"""
import itertools
from dataclasses import dataclass
from typing import Optional

from kubernetes.client import (
    V1Deployment,
    V1Container,
    V1DeploymentSpec,
    V1ObjectMeta,
    V1PodSpec,
    V1RollingUpdateDeployment,
    V1LabelSelector,
    V1ContainerPort,
    V1EnvVar,
    V1Service,
    V1ServiceSpec,
    V1ServicePort,
    V1ServiceAccount,
    V1LocalObjectReference,
    V1EnvVarSource,
    V1SecretKeySelector,
    V1Probe,
    ApiClient,
    V1HTTPGetAction,
    V1ResourceRequirements,
    V1PodTemplateSpec,
    V1DeploymentStrategy,
    V1Job,
    V1JobSpec,
    V1CronJob,
    V1CronJobSpec,
    V1JobTemplateSpec,
    V1ConfigMap,
    V1Role,
    V1RoleBinding,
    V1PolicyRule,
    V1RoleRef,
    V1Subject,
)
from ruamel.yaml import YAML

from . import substitute_namespaces, get_namespace
from .resources import (
    CustomResourceDefinition,
    to_dict,
)  # pylint: disable = no-name-in-module
from .resources.prometheus import V1PrometheusRule, V1ServiceMonitor
from .resources.sealed_secret import V1SealedSecret
from .resources.spark import (
    to_spark_body,
    get_spark_config_map_data,
    V1SparkApplication,
)
from .resources.traefik import (
    V1AlphaIngressRoute,
    V1AlphaMiddleware,
    HostWrapper,
)  # pylint: disable = no-name-in-module
from ...models import Input
from ....project import (
    Project,
    KeyValueProperty,
    Probe,
    Deployment,
    TargetProperty,
    Resources,
    Target,
    Kubernetes,
    Job,
    Traefik,
    TraefikHost,
    get_env_variables,
    Alert,
    KeyValueRef,
    Metrics,
)
from ....stages.discovery import DeploySet
from ....utilities.docker import DockerImageSpec

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
            return type(obj)(
                (k, try_parse_target(with_targets_parsed(v), target))
                for k, v in obj.items()
            )

        return obj

    return with_targets_parsed(dictionary)


@dataclass(frozen=True)
class ResourceDefaults:
    instances: TargetProperty[int]
    cpus: TargetProperty[float]
    mem: TargetProperty[int]

    @staticmethod
    def from_config(resources: dict):
        limit = resources["limit"]
        return ResourceDefaults(
            instances=TargetProperty.from_config(resources["instances"]),
            cpus=TargetProperty.from_config(limit["cpus"]),
            mem=TargetProperty.from_config(limit["mem"]),
        )


@dataclass(frozen=True)
class DefaultWhitelistAddress:
    name: str
    host: TargetProperty[list[str]]

    @staticmethod
    def from_config(values: dict):
        return DefaultWhitelistAddress(
            name=values["name"],
            host=TargetProperty.from_config(values),
        )


@dataclass(frozen=True)
class DefaultWhitelists:
    default: list[str]
    addresses: list[DefaultWhitelistAddress]

    @staticmethod
    def from_config(values: dict):
        if values is None:
            return None
        return DefaultWhitelists(
            default=values["default"],
            addresses=[
                DefaultWhitelistAddress.from_config(address)
                for address in values["addresses"]
            ],
        )


@dataclass(frozen=True)
class DeploymentDefaults:
    resources_defaults: ResourceDefaults
    liveness_probe_defaults: dict
    startup_probe_defaults: dict
    job_defaults: dict
    traefik_defaults: dict
    white_lists: DefaultWhitelists
    image_pull_secrets: dict

    @staticmethod
    def from_config(config: dict):
        deployment_values = config.get("project", {}).get("deployment", {})
        if deployment_values is None:
            raise KeyError("Configuration should have project.deployment section")
        kubernetes = deployment_values.get("kubernetes", {})
        return DeploymentDefaults(
            resources_defaults=ResourceDefaults.from_config(kubernetes["resources"]),
            liveness_probe_defaults=kubernetes["livenessProbe"],
            startup_probe_defaults=kubernetes["startupProbe"],
            job_defaults=kubernetes.get("job", {}),
            traefik_defaults=deployment_values.get("traefik", {}),
            white_lists=DefaultWhitelists.from_config(config.get("whiteLists", {})),
            image_pull_secrets=kubernetes.get("imagePullSecrets", {}),
        )


class ChartBuilder:
    step_input: Input
    project: Project
    mappings: dict[int, int]
    env: list[KeyValueProperty]
    sealed_secrets: list[KeyValueProperty]
    secrets: list[KeyValueRef]
    deployment: Deployment
    target: Target
    release_name: str
    config_defaults: DeploymentDefaults
    deploy_set: Optional[DeploySet]
    namespace: str
    role: Optional[dict]

    def __init__(self, step_input: Input, deploy_set: Optional[DeploySet] = None):
        self.step_input = step_input
        project = self.step_input.project
        self.project = project
        if project.deployment is None:
            raise AttributeError("deployment field should be set")

        self.config_defaults = DeploymentDefaults.from_config(
            step_input.run_properties.config
        )

        self.deployment = project.deployment
        properties = self.deployment.properties
        self.env = properties.env if properties and properties.env else []
        self.sealed_secrets = (
            properties.sealed_secret if properties and properties.sealed_secret else []
        )
        self.secrets = (
            properties.kubernetes if properties and properties.kubernetes else []
        )
        self.mappings = self.project.kubernetes.port_mappings
        self.target = step_input.run_properties.target
        self.release_name = self.project.name.lower()
        self.deploy_set = deploy_set
        self.namespace = get_namespace(
            run_properties=step_input.run_properties, project=project
        )
        self.role = project.kubernetes.role

    def _to_labels(self) -> dict:
        run_properties = self.step_input.run_properties
        app_labels = {
            "name": self.release_name,
            "app.kubernetes.io/version": run_properties.versioning.identifier,
            "app.kubernetes.io/managed-by": "Helm",
            "app.kubernetes.io/name": self.release_name,
            "app.kubernetes.io/instance": self.release_name,
        }

        if len(self.project.maintainer) > 0:
            app_labels["maintainers"] = ".".join(self.project.maintainer).replace(
                " ", "_"
            )
            app_labels["maintainer"] = self.project.maintainer[0].replace(" ", "_")

        app_labels["version"] = run_properties.versioning.identifier

        if run_properties.versioning.revision:
            app_labels["revision"] = run_properties.versioning.revision

        return app_labels

    def _to_annotations(self) -> dict:
        return {"description": self.project.description}

    def _to_image_annotation(self) -> dict:
        return {"image": self._get_image()}

    def _to_object_meta(
        self, name: Optional[str] = None, annotations: Optional[dict] = None
    ) -> V1ObjectMeta:
        return V1ObjectMeta(
            name=name if name else self.release_name,
            labels=self._to_labels(),
            annotations=annotations,
        )

    def _to_selector(self):
        return V1LabelSelector(
            match_labels={
                "app.kubernetes.io/instance": self.release_name,
                "app.kubernetes.io/name": self.release_name,
            }
        )

    @staticmethod
    def _to_k8s_model(values: dict, model_type):
        return ApiClient()._ApiClient__deserialize(  # pylint: disable=protected-access
            values, model_type
        )

    @staticmethod
    def _to_probe(probe: Optional[Probe], defaults: dict, target: Target) -> V1Probe:
        values = defaults.copy()
        if probe:
            values.update(probe.values)
        v1_probe: V1Probe = ChartBuilder._to_k8s_model(values, V1Probe)
        path = probe.path.get_value(target) if probe else None
        v1_probe.http_get = V1HTTPGetAction(
            path="/health" if path is None else path, port="port-0"
        )
        return v1_probe

    def _construct_probes(self) -> tuple[Optional[V1Probe], Optional[V1Probe]]:
        """
        Construct kubernetes probes based on project yaml values and default values in mpyl_config.yaml.

        NOTE: If no startup probe was provided in the project yaml, but a liveness probe was,
              this method constructs a startup probe from the default values!
        :return:
        """
        liveness_probe = (
            ChartBuilder._to_probe(
                self.project.kubernetes.liveness_probe,
                self.config_defaults.liveness_probe_defaults,
                self.target,
            )
            if self.project.kubernetes.liveness_probe
            else None
        )

        startup_probe = (
            ChartBuilder._to_probe(
                self.project.kubernetes.startup_probe,
                self.config_defaults.startup_probe_defaults,
                self.target,
            )
            if self.project.kubernetes.liveness_probe
            else None
        )

        return liveness_probe, startup_probe

    def to_service(self) -> V1Service:
        service_ports = list(
            map(
                lambda key: V1ServicePort(
                    port=int(key),
                    target_port=int(self.mappings[key]),
                    protocol="TCP",
                    name=f"{key}-webservice-port",
                ),
                self.mappings.keys(),
            )
        )

        return V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(
                annotations=self._to_annotations(),
                name=self.release_name,
                labels=self._to_labels(),
            ),
            spec=V1ServiceSpec(
                type="ClusterIP",
                ports=service_ports,
                selector=self._to_selector().match_labels,
            ),
        )

    def to_job(self) -> V1Job:
        job_container = V1Container(
            name=self.release_name,
            image=self._get_image(),
            env=self._get_env_vars(),
            image_pull_policy="Always",
            resources=self._get_resources(),
        )

        pod_template = V1PodTemplateSpec(
            metadata=self._to_object_meta(annotations=self._to_image_annotation()),
            spec=V1PodSpec(
                containers=[job_container],
                service_account=self.release_name,
                service_account_name=self.release_name,
                restart_policy="Never",
            ),
        )

        defaults = with_target(self.config_defaults.job_defaults, self.target)
        specified = defaults | with_target(self.project.job.job, self.target)

        template_dict = to_dict(pod_template)
        specified["template"] = template_dict
        spec: V1JobSpec = ChartBuilder._to_k8s_model(specified, V1JobSpec)

        return V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=self._to_object_meta(),
            spec=spec,
        )

    def to_cron_job(self) -> V1CronJob:
        values = self.project.job.cron
        job_template = V1JobTemplateSpec(spec=self.to_job().spec)
        template_dict = to_dict(job_template)
        values["jobTemplate"] = template_dict
        v1_cron_job_spec: V1CronJobSpec = ChartBuilder._to_k8s_model(
            values, V1CronJobSpec
        )
        return V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=self._to_object_meta(),
            spec=v1_cron_job_spec,
        )

    def to_spark_application(self) -> V1SparkApplication:
        return V1SparkApplication(
            metadata=self._to_object_meta(),
            schedule=self._get_job().cron["schedule"],
            body=to_spark_body(
                project_name=self.release_name,
                env_vars=get_env_variables(self.project, self.target),
                spark=self._get_job().spark,
                image=self._get_image(),
                command=self.project.kubernetes.command.get_value(self.target).split(
                    " "
                )
                if self.project.kubernetes.command
                else None,
                env_secret_key_refs={
                    s.key: {"key": s.key, "name": self.release_name}
                    for s in self.sealed_secrets
                },
                num_replicas=self.project.kubernetes.resources.instances.get_value(
                    self.target
                )
                if self.project.kubernetes.resources.instances
                else 1,
            ),
        )

    def to_spark_config_map(self) -> V1ConfigMap:
        return V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            data=get_spark_config_map_data(),
            metadata=self._to_object_meta(),
        )

    def to_prometheus_rule(self, alerts: list[Alert]) -> V1PrometheusRule:
        return V1PrometheusRule(
            metadata=self._to_object_meta(
                name=f"{self.project.name.lower()}-prometheus-rule"
            ),
            alerts=alerts,
        )

    def to_service_monitor(self, metrics: Metrics) -> V1ServiceMonitor:
        return V1ServiceMonitor(
            metadata=self._to_object_meta(
                name=f"{self.project.name.lower()}-service-monitor"
            ),
            metrics=metrics,
            default_port=self.__find_default_port(),
            namespace=self.namespace,
            release_name=self.release_name,
        )

    def __find_default_port(self) -> int:
        found = next(iter(self.mappings.keys()))
        if found:
            return int(found)
        raise KeyError("No default port found. Did you define a port mapping?")

    def create_host_wrappers(self) -> list[HostWrapper]:
        default_hosts: list[TraefikHost] = Traefik.from_config(
            self.config_defaults.traefik_defaults
        ).hosts

        hosts: list[TraefikHost] = (
            self.deployment.traefik.hosts if self.deployment.traefik else []
        )

        address_dictionary = {
            address.name: address.host.get_value(self.target)
            for address in self.config_defaults.white_lists.addresses
        }

        def to_white_list(
            configured: Optional[TargetProperty[list[str]]],
        ) -> dict[str, list[str]]:
            white_lists = self.config_defaults.white_lists.default
            if configured and configured.get_value(self.target):
                white_lists = white_lists + configured.get_value(self.target)

            return dict(
                filter(lambda x: x[0] in white_lists, address_dictionary.items())
            )

        return [
            HostWrapper(
                traefik_host=host,
                name=self.release_name,
                index=idx,
                service_port=host.service_port
                if host.service_port
                else self.__find_default_port(),
                white_lists=to_white_list(host.whitelists),
                tls=host.tls.get_value(self.target) if host.tls else None,
                insecure=host.insecure,
            )
            for idx, host in enumerate(hosts if hosts else default_hosts)
        ]

    def to_ingress_routes(self, https: bool) -> list[V1AlphaIngressRoute]:
        hosts = self.create_host_wrappers()
        return [
            V1AlphaIngressRoute(
                metadata=self._to_object_meta(
                    name=f"{self.release_name}-ingress-{i}-http"
                    + ("s" if https else "")
                ),
                host=host,
                target=self.target,
                namespace=get_namespace(self.step_input.run_properties, self.project),
                pr_number=self.step_input.run_properties.versioning.pr_number,
                https=https,
            )
            for i, host in enumerate(hosts)
        ]

    def to_middlewares(self) -> dict[str, V1AlphaMiddleware]:
        hosts: list[HostWrapper] = self.create_host_wrappers()

        def to_metadata(host: HostWrapper) -> V1ObjectMeta:
            metadata = self._to_object_meta(name=host.full_name)
            # metadata.annotations = host.white_lists
            metadata.annotations = {
                k: ", ".join(v) for k, v in host.white_lists.items()
            }
            return metadata

        return {
            host.full_name: V1AlphaMiddleware(
                metadata=to_metadata(host),
                source_ranges=list(itertools.chain(*host.white_lists.values())),
            )
            for host in hosts
        }

    def to_service_account(
        self,
    ) -> V1ServiceAccount:
        kubernetes = self._get_kubernetes()
        image_pull_secrets_config = (
            kubernetes.image_pull_secrets or self.config_defaults.image_pull_secrets
        )
        secrets = [
            ChartBuilder._to_k8s_model(
                secret,
                V1LocalObjectReference,
            )
            for secret in image_pull_secrets_config
        ]
        return V1ServiceAccount(
            api_version="v1",
            kind="ServiceAccount",
            metadata=self._to_object_meta(),
            image_pull_secrets=secrets,
        )

    def to_role(self, role: dict) -> V1Role:
        return V1Role(
            api_version="rbac.authorization.k8s.io/v1",
            kind="Role",
            metadata=self._to_object_meta(),
            rules=[
                ChartBuilder._to_k8s_model({"apiGroups": [""]} | role, V1PolicyRule)
            ],
        )

    def to_role_binding(self) -> V1RoleBinding:
        return V1RoleBinding(
            api_version="rbac.authorization.k8s.io/v1",
            kind="RoleBinding",
            metadata=self._to_object_meta(),
            role_ref=V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name=self.release_name,
            ),
            subjects=[
                V1Subject(
                    kind="ServiceAccount",
                    name=self.release_name,
                    namespace=self.namespace,
                )
            ],
        )

    def to_sealed_secrets(self) -> V1SealedSecret:
        secrets: dict[str, str] = {}
        for secret in self.sealed_secrets:
            secrets[secret.key] = secret.get_value(self.target)

        return V1SealedSecret(name=self.release_name, secrets=secrets)

    @staticmethod
    def _to_resource_requirements(
        resources: Resources, defaults: ResourceDefaults, target: Target
    ):
        cpus = (
            resources.limit.cpus
            if resources.limit and resources.limit.cpus
            else defaults.cpus
        )

        cpus_limit: float = cpus.get_value(target=target) * 1000.0

        cpus_request: float = (
            resources.request.cpus.get_value(target=target) * 1000.0
            if resources.request and resources.request.cpus
            else cpus_limit * CPU_REQUEST_SCALE_FACTOR
        )

        mem = (
            resources.limit.mem
            if resources.limit and resources.limit.mem
            else defaults.mem
        )
        mem_limit: float = mem.get_value(target=target)

        mem_request: float = (
            resources.request.mem.get_value(target=target)
            if resources.request and resources.request.mem
            else mem_limit * MEM_REQUEST_SCALE_FACTOR
        )

        return V1ResourceRequirements(
            limits={"cpu": f"{int(cpus_limit)}m", "memory": f"{int(mem_limit)}Mi"},
            requests={
                "cpu": f"{int(cpus_request)}m",
                "memory": f"{int(mem_request)}Mi",
            },
        )

    def _get_image(self):
        return self.step_input.as_spec(DockerImageSpec).image

    def _get_resources(self):
        resources = self.project.kubernetes.resources
        defaults = self.config_defaults.resources_defaults
        return ChartBuilder._to_resource_requirements(resources, defaults, self.target)

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

    def _create_sealed_secret_env_vars(
        self, secret_list: list[KeyValueProperty]
    ) -> list[V1EnvVar]:
        return [
            V1EnvVar(
                name=e.key,
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        key=e.key, name=self.release_name, optional=False
                    )
                ),
            )
            for e in secret_list
        ]

    def _map_key_value_refs(self, ref: KeyValueRef) -> V1EnvVar:
        value_from = self._to_k8s_model(ref.value_from, V1EnvVarSource)

        return V1EnvVar(name=ref.key, value_from=value_from)

    def _create_secret_env_vars(self, secret_list: list[KeyValueRef]) -> list[V1EnvVar]:
        return list(map(self._map_key_value_refs, secret_list))

    @staticmethod
    def extract_raw_env(target: Target, env: list[KeyValueProperty]):
        raw_env_vars = {
            e.key: e.get_value(target) for e in env if e.get_value(target) is not None
        }
        return raw_env_vars

    def _get_env_vars(self):
        raw_env_vars = self.extract_raw_env(self.target, self.env)
        pr_identifier = (
            None
            if self.step_input.run_properties.versioning.tag
            else self.step_input.run_properties.versioning.pr_number
        )
        processed_env_vars = (
            substitute_namespaces(
                raw_env_vars,
                {p.to_name for p in self.deploy_set.all_projects},
                {p.to_name for p in self.deploy_set.projects_to_deploy},
                pr_identifier,
            )
            if self.deploy_set
            else raw_env_vars
        )

        env_vars = [
            V1EnvVar(name=key, value=value) for key, value in processed_env_vars.items()
        ]

        sealed_secrets_for_target = list(
            filter(lambda v: v.get_value(self.target) is not None, self.sealed_secrets)
        )
        sealed_secrets = self._create_sealed_secret_env_vars(sealed_secrets_for_target)
        secrets = self._create_secret_env_vars(self.secrets)

        return env_vars + sealed_secrets + secrets

    @property
    def is_cron_job(self) -> bool:
        return len(self._get_job().cron.keys()) > 0

    def to_deployment(self) -> V1Deployment:
        ports = [
            V1ContainerPort(
                container_port=self.mappings[key], protocol="TCP", name=f"port-{idx}"
            )
            for idx, key in enumerate(self.mappings.keys())
        ]

        project = self.project
        resources = project.resources
        defaults = self.config_defaults.resources_defaults

        liveness_probe, startup_probe = self._construct_probes()

        container = V1Container(
            name="service",
            image=self._get_image(),
            env=self._get_env_vars(),
            ports=ports,
            image_pull_policy="Always",
            resources=ChartBuilder._to_resource_requirements(
                resources, defaults, self.target
            ),
            liveness_probe=liveness_probe,
            startup_probe=startup_probe,
            command=(
                self.project.kubernetes.command.get_value(self.target).split(" ")
                if self.project.kubernetes.command
                else None
            ),
            args=(
                self.project.kubernetes.args.get_value(self.target).split(" ")
                if self.project.kubernetes.args
                else None
            ),
        )

        instances = resources.instances if resources.instances else defaults.instances

        return V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=V1ObjectMeta(
                annotations=self._to_annotations(),
                name=self.release_name,
                labels=self._to_labels(),
            ),
            spec=V1DeploymentSpec(
                replicas=instances.get_value(target=self.target),
                template=V1PodTemplateSpec(
                    metadata=self._to_object_meta(),
                    spec=V1PodSpec(
                        containers=[container],
                        service_account=self.release_name,
                        service_account_name=self.release_name,
                    ),
                ),
                strategy=V1DeploymentStrategy(
                    rolling_update=V1RollingUpdateDeployment(
                        max_surge="25%", max_unavailable="25%"
                    ),
                    type="RollingUpdate",
                ),
                selector=self._to_selector(),
            ),
        )

    def to_common_chart(self) -> dict[str, CustomResourceDefinition]:
        chart = {"service-account": self.to_service_account()}

        if self.sealed_secrets:
            chart["sealed-secrets"] = self.to_sealed_secrets()

        if self.role:
            chart["role"] = self.to_role(self.role)
            chart["rolebinding"] = self.to_role_binding()

        return chart


def to_service_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return (
        builder.to_common_chart()
        | _to_service_components_chart(builder)
        | builder.to_middlewares()
    )


def _to_service_components_chart(builder):
    common_chart = {
        "deployment": builder.to_deployment(),
        "service": builder.to_service(),
    }
    metrics = builder.project.kubernetes.metrics
    prometheus_chart = (
        {
            "prometheus-rule": builder.to_prometheus_rule(
                alerts=builder.project.kubernetes.metrics.alerts
            ),
            "service-monitor": builder.to_service_monitor(metrics=metrics),
        }
        if metrics and metrics.enabled
        else {}
    )
    ingress_https = {
        f"{builder.project.name}-ingress-{i}-https": route
        for i, route in enumerate(builder.to_ingress_routes(https=True))
    }
    ingress_http = {
        f"{builder.project.name}-ingress-{i}-http": route
        for i, route in enumerate(builder.to_ingress_routes(https=False))
    }
    return common_chart | prometheus_chart | ingress_https | ingress_http


def to_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {"job": builder.to_job()}


def to_cron_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {"cronjob": builder.to_cron_job()}


def to_spark_job_chart(builder: ChartBuilder) -> dict[str, CustomResourceDefinition]:
    return builder.to_common_chart() | {
        "spark": builder.to_spark_application(),
        "config-map": builder.to_spark_config_map(),
    }
