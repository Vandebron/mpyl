"""
This module contains the traefik ingress route CRD.
"""
from dataclasses import dataclass
from typing import Optional

from kubernetes.client import V1ObjectMeta

from . import CustomResourceDefinition
from .....project import Host, Target


@dataclass(frozen=True)
class HostWrapper:
    host: Host
    name: str
    index: int
    service_port: int
    white_lists: dict[str, list[str]]

    @property
    def full_name(self) -> str:
        return f'{self.name}-ingress-{self.index}-whitelist'


class V1AlphaIngressRoute(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, hosts: list[HostWrapper], target: Target,
                 pr_number: Optional[int]):
        def _interpolate_names(host: str, name: str) -> str:
            host = host.replace('{SERVICE-NAME}', name)
            if pr_number:
                return host.replace('{PR-NUMBER}', str(pr_number))
            return host

        routes = [{'kind': 'Rule', 'match': _interpolate_names(host.host.host.get_value(target), host.name),
                   'services': [{'name': host.name, 'kind': 'Service', 'port': host.service_port}],
                   'middlewares':
                       [{'name': host.full_name}, {'name': 'traefik-https-redirect@kubernetescrd'}]} for host in hosts]

        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="IngressRoute", metadata=metadata,
                         spec={'routes': routes, 'entryPoints': ['websecure'],
                               'tls': {'secretName': 'le-prod-wildcard-cert'}}, schema='traefik.ingress.schema.yml')


class V1AlphaMiddleware(CustomResourceDefinition):

    def __init__(self, metadata: V1ObjectMeta, source_ranges: list[str]):
        super().__init__(api_version='traefik.containo.us/v1alpha1', kind="Middleware", metadata=metadata,
                         spec={'ipWhiteList': {'sourceRange': source_ranges}}, schema='traefik.middleware.schema.yml')
