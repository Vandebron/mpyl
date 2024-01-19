"""
This module contains the sealed secret CRD.
"""

from kubernetes.client import V1ObjectMeta

from . import CustomResourceDefinition


class V1SealedSecret(CustomResourceDefinition):
    def __init__(self, name: str, secrets: dict[str, str]):
        super().__init__(
            api_version="bitnami.com/v1alpha1",
            kind="SealedSecret",
            metadata=V1ObjectMeta(
                name=name,
                labels={"chart": "service-0.1.0"},
                annotations={"sealedsecrets.bitnami.com/cluster-wide": "true"},
            ),
            spec={"encryptedData": secrets},
        )
