"""
Custom Resource Definitions, implementing `mpyl.steps.deploy.k8s.resources.crd.CustomResourceDefinition`
"""
from typing import Optional

from kubernetes.client import V1ObjectMeta

from .crd import CustomResourceDefinition
from .....project import Host, Target


class V1SealedSecret(CustomResourceDefinition):
    def __init__(self, name: str, secrets: dict[str, str]):
        super().__init__(api_version="bitnami.com/v1alpha1", kind="SealedSecret",
                         metadata=V1ObjectMeta(name=name, labels={'chart': 'service-0.1.0'},
                                               annotations={'sealedsecrets.bitnami.com/cluster-wide': 'true'}),
                         spec={'encryptedData': secrets})


class V1AlphaIngressRoute(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, hosts: list[Host], service_port: int, name: str, target: Target):
        routes = [{'kind': 'Rule', 'match': host.host.get_value(target),
                   'services': [{'name': name, 'kind': 'Service', 'port': service_port}],
                   'middlewares': [{'name': f'{name}-ingress-{idx}-whitelist'}]} for idx, host in enumerate(hosts)]

        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="IngressRoute", metadata=metadata,
                         spec={'routes': routes}, schema='traeffik.schema.yml')


class V1SparkApplication(CustomResourceDefinition):
    def __init__(self, schedule: Optional[str], body: dict):
        if schedule:
            super().__init__(api_version="sparkoperator.k8s.io/v1beta2", kind="ScheduledSparkApplication",
                             metadata=V1ObjectMeta(name="sparkapplications.sparkoperator.k8s.io"),
                             schema="sparkoperator.k8s.io_scheduledsparkapplications.yaml",
                             spec={'schedule': schedule,
                                   'template': body})
        else:
            super().__init__(api_version="sparkoperator.k8s.io/v1beta2", kind="SparkApplication",
                             metadata=V1ObjectMeta(name="sparkapplications.sparkoperator.k8s.io"),
                             schema="sparkoperator.k8s.io_sparkapplications.yaml",
                             spec={'spec': body})
