"""
This module contains the traefik ingress route CRD.
"""
from kubernetes.client import V1ObjectMeta

from . import CustomResourceDefinition
from .....project import Host, Target


class V1AlphaIngressRoute(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, hosts: list[Host], service_port: int, name: str, target: Target):
        routes = [{'kind': 'Rule', 'match': host.host.get_value(target),
                   'services': [{'name': name, 'kind': 'Service', 'port': service_port}],
                   'middlewares': [{'name': f'{name}-ingress-{idx}-whitelist'}]} for idx, host in enumerate(hosts)]

        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="IngressRoute", metadata=metadata,
                         spec={'routes': routes}, schema='traeffik.schema.yml')
