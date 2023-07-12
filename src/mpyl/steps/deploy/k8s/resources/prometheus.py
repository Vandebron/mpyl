"""
This module contains the PrometheusRule CRD
"""

from kubernetes.client import V1ObjectMeta

from .....project import Alert
from .. import CustomResourceDefinition


def _alerts_to_rules(alerts: list[Alert]) -> list[dict]:
    return [
        {
            "alert": alert.name,
            "annotations": {
                "description": alert.description,
            },
            "expr": alert.expr,
            "for": alert.for_duration,
            "labels": {
                "alertname": alert.name,
                "severity": alert.severity,
            },
        }
        for alert in alerts
    ]


class V1PrometheusRule(CustomResourceDefinition):
    def __init__(self, metadata: V1ObjectMeta, alerts: list[Alert]):
        super().__init__(
            api_version="monitoring.coreos.com/v1",
            kind="PrometheusRule",
            metadata=metadata,
            schema="monitoring.coreos.com_prometheuses.schema.yml",
            spec={
                "groups": [
                    {
                        "name": f"{metadata.name}-group",
                        "rules": _alerts_to_rules(alerts),
                    }
                ]
            },
        )
