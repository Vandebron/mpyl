"""
This module contains the traefik ingress route CRD.
"""
from typing import Optional

from kubernetes.client import V1ObjectMeta

from . import CustomResourceDefinition
from .....project import Host, Target


class V1AlphaIngressRoute(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, hosts: list[Host], service_port: int, name: str, target: Target,
                 pr_number: Optional[int]):
        def _interpolate_names(host: str) -> str:
            host = host.replace('{SERVICE-NAME}', name)
            if pr_number:
                return host.replace('{PR-NUMBER}', str(pr_number))
            return host

        routes = [{'kind': 'Rule', 'match': _interpolate_names(host.host.get_value(target)),
                   'services': [{'name': name, 'kind': 'Service', 'port': service_port}],
                   'middlewares': [{'name': f'{name}-ingress-{idx}-whitelist'}]} for idx, host in enumerate(hosts)]

        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="IngressRoute", metadata=metadata,
                         spec={'routes': routes, 'entryPoints': ['websecure']}, schema='traeffik.ingress.schema.yml')

    def get_middle_wares(self) -> list[str]:
        return [middleware['name'] for route in self.spec['routes'] for middleware in route['middlewares']]


class V1AlphaMiddleware(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, source_ranges: list[str]):
        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="Middleware", metadata=metadata,
                         spec={'ipWhiteList': {'sourceRange': source_ranges}}, schema='traeffik.middleware.schema.yml')
