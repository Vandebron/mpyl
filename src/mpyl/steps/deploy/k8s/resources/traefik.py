"""
This module contains the traefik ingress route CRD.
"""

from dataclasses import dataclass
from typing import Optional, Union, Any

from kubernetes.client import V1ObjectMeta

from . import CustomResourceDefinition
from .....project import TraefikHost, Target, TraefikAdditionalRoute
from .....utilities import replace_pr_number


@dataclass(frozen=True)
class HostWrapper:
    traefik_host: TraefikHost
    name: str
    index: int
    service_port: int
    white_lists: dict[str, list[str]]
    tls: Optional[str]
    additional_route: Optional[TraefikAdditionalRoute]
    insecure: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.name}-ingress-{self.index}-whitelist"


class V1AlphaIngressRoute(CustomResourceDefinition):
    def __init__(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        metadata: V1ObjectMeta,
        host: HostWrapper,
        target: Target,
        namespace: str,
        cluster_env: str,
        pr_number: Optional[int],
        middlewares_override: list[str],
        entrypoints_override: list[str],
        http_middleware: str,
        default_tls: str,
        https: bool = True,
    ):
        def _interpolate_names(host: str, name: str, cluster_env: str) -> str:
            host = host.replace("{SERVICE-NAME}", name)
            host = host.replace("{namespace}", namespace)
            host = host.replace("{CLUSTER-ENV}", cluster_env)
            host = replace_pr_number(host, pr_number)
            return host

        combined_middlewares = (
            [
                {"name": http_middleware} if not https else None,
                {"name": host.full_name},
            ]
            if len(middlewares_override) == 0
            else [{"name": m for m in middlewares_override}]
        )

        route: dict[str, Any] = {
            "kind": "Rule",
            "match": _interpolate_names(
                host=host.traefik_host.host.get_value(target),
                name=host.name,
                cluster_env=cluster_env,
            ),
            "services": [
                {"name": host.name, "kind": "Service", "port": host.service_port}
            ],
            "middlewares": combined_middlewares,
        }

        if host.traefik_host.priority:
            route |= {"priority": host.traefik_host.priority.get_value(target)}

        tls: dict[str, Union[str, dict]] = {
            "secretName": host.tls if host.tls else default_tls
        }

        if host.insecure:
            tls |= {"options": {"name": "insecure-ciphers", "namespace": "traefik"}}

        combined_entrypoints = (
            ["websecure" if https else "web"]
            if len(entrypoints_override) == 0
            else entrypoints_override
        )

        super().__init__(
            api_version="traefik.io/v1alpha1",
            kind="IngressRoute",
            metadata=metadata,
            spec={
                "routes": [route],
                "entryPoints": combined_entrypoints,
                "tls": tls if https else None,
            },
            schema="traefik.ingress.schema.yml",
        )


class V1AlphaMiddleware(CustomResourceDefinition):
    def __init__(self, metadata: V1ObjectMeta, source_ranges: list[str]):
        super().__init__(
            api_version="traefik.io/v1alpha1",
            kind="Middleware",
            metadata=metadata,
            spec={"ipAllowList": {"sourceRange": source_ranges}},
            schema="traefik.middleware.schema.yml",
        )
