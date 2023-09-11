"""
Custom Resource Definitions, allow you to create custom k8s resources, besides the default ones.
This is useful for example when you want to configure a specific operator, like Spark or sealed secrets.
"""
import pkgutil
from typing import Optional

import jsonschema
import six
from jsonschema import ValidationError
from kubernetes.client import Configuration, V1ObjectMeta
from ruamel.yaml import YAML

from .....projects.versioning import yaml_to_string

yaml = YAML()


class CustomResourceDefinition:
    openapi_types = {
        "api_version": "str",
        "kind": "str",
        "metadata": "V1ObjectMeta",
        "spec": "dict",
    }

    attribute_map = {
        "api_version": "apiVersion",
        "kind": "kind",
        "metadata": "metadata",
        "spec": "spec",
    }

    def __init__(
        self,
        api_version: str,
        kind: str,
        metadata: V1ObjectMeta,
        spec: dict,
        local_vars_configuration=None,
        schema: Optional[str] = None,
    ):  # noqa: E501
        """V1CSIDriver - a model defined in OpenAPI"""  # noqa: E501
        if local_vars_configuration is None:
            local_vars_configuration = Configuration()
        self.local_vars_configuration = local_vars_configuration

        self._api_version = api_version
        self._kind = kind
        self._metadata = metadata
        self._spec = spec
        self._schema = schema
        self.discriminator = None

        if api_version is not None:
            self.api_version = api_version
        if kind is not None:
            self.kind = kind
        if metadata is not None:
            self.metadata = metadata

    @property
    def schema(self) -> Optional[str]:
        return self._schema

    @property
    def api_version(self) -> str:
        return self._api_version

    @api_version.setter
    def api_version(self, api_version):
        self._api_version = api_version

    @property
    def kind(self) -> str:
        return self._kind

    @kind.setter
    def kind(self, kind):
        self._kind = kind

    @property
    def metadata(self) -> V1ObjectMeta:
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        self._metadata = metadata

    @property
    def spec(self) -> dict:
        return self._spec

    @spec.setter
    def spec(self, spec):
        if (
            self.local_vars_configuration.client_side_validation and spec is None
        ):  # noqa: E501
            raise ValueError(
                "Invalid value for `spec`, must not be `None`"
            )  # noqa: E501
        self._spec = spec


def to_dict(obj):
    result = {}

    for attr, _ in six.iteritems(obj.openapi_types):
        value = getattr(obj, attr)
        key = obj.attribute_map.get(attr)
        if isinstance(value, list):
            result[key] = list(
                map(lambda x: to_dict(x) if hasattr(x, "to_dict") else x, value)
            )
        elif hasattr(value, "to_dict"):
            result[key] = to_dict(value)
        elif isinstance(value, dict):
            result[key] = dict(  # type: ignore
                map(
                    lambda item: (item[0], to_dict(item[1]))
                    if hasattr(item[1], "to_dict")
                    else item,
                    value.items(),
                )
            )
        else:
            result[key] = value

    return result


def to_yaml(resource: object) -> str:
    def remove_none(obj):
        if isinstance(obj, (list, tuple, set)):
            return type(obj)(remove_none(x) for x in obj if x is not None)
        if isinstance(obj, dict):
            return type(obj)(
                (remove_none(k), remove_none(v))
                for k, v in obj.items()
                if k is not None and v is not None
            )
        return obj

    resource_dict = (
        to_dict(resource)
        if (hasattr(resource, "openapi_types") and hasattr(resource, "attribute_map"))
        else {}
    )
    yaml_values = remove_none(resource_dict)

    if hasattr(resource, "schema") and resource.schema:
        template = pkgutil.get_data(__name__, f"schema/{resource.schema}")
        if template:
            schema = yaml.load(template.decode("utf-8"))
            try:
                jsonschema.validate(yaml_values, schema)
            except ValidationError as err:
                raise ValueError(
                    f'Schema validation failed with {err.message} at {".".join(map(str, err.schema_path))}'
                ) from err
        else:
            raise ValueError(
                f"Schema {resource.schema} defined but not found in package"
            )

    return yaml_to_string(yaml_values, yaml)
