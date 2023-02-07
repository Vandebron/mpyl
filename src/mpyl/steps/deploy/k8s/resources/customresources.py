from kubernetes.client import V1ObjectMeta

from src.mpyl.project import Host
from src.mpyl.target import Target
from .crd import CustomResourceDefinition


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
