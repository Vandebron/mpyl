from io import StringIO

import six
from kubernetes.client import Configuration, V1ObjectMeta
from ruamel.yaml import YAML

yaml = YAML()


class KubernetesResource:
    openapi_types = {
        'api_version': 'str',
        'kind': 'str',
        'metadata': 'V1ObjectMeta',
        'spec': 'dict'
    }

    attribute_map = {
        'api_version': 'apiVersion',
        'kind': 'kind',
        'metadata': 'metadata',
        'spec': 'spec'
    }

    def __init__(self, api_version: str, kind: str, metadata: V1ObjectMeta, spec: dict,
                 local_vars_configuration=None):  # noqa: E501
        """V1CSIDriver - a model defined in OpenAPI"""  # noqa: E501
        if local_vars_configuration is None:
            local_vars_configuration = Configuration()
        self.local_vars_configuration = local_vars_configuration

        self._api_version = api_version
        self._kind = kind
        self._metadata = metadata
        self._spec = spec
        self.discriminator = None

        if api_version is not None:
            self.api_version = api_version
        if kind is not None:
            self.kind = kind
        if metadata is not None:
            self.metadata = metadata

    @property
    def api_version(self):
        return self._api_version

    @api_version.setter
    def api_version(self, api_version):
        self._api_version = api_version

    @property
    def kind(self):
        return self._kind

    @kind.setter
    def kind(self, kind):
        self._kind = kind

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        self._metadata = metadata

    @property
    def spec(self):
        return self._spec

    @spec.setter
    def spec(self, spec):
        if self.local_vars_configuration.client_side_validation and spec is None:  # noqa: E501
            raise ValueError("Invalid value for `spec`, must not be `None`")  # noqa: E501
        self._spec = spec

    def to_dict(self):
        pass


class V1SealedSecret(KubernetesResource):
    def __init__(self, name: str, secrets: dict[str, str]):
        super().__init__(api_version="bitnami.com/v1alpha1", kind="SealedSecret",
                         metadata=V1ObjectMeta(name=name, labels={'chart': 'service-0.1.0'},
                                               annotations={'sealedsecrets.bitnami.com/cluster-wide': 'true'}),
                         spec={'encryptedData': secrets})


def camel_case(text):
    return ''.join(word.title() if i else word for i, word in enumerate(text.split('_')))


def to_dict(obj):
    result = {}

    for attr, _ in six.iteritems(obj.openapi_types):
        value = getattr(obj, attr)
        key = obj.attribute_map.get(attr)
        if isinstance(value, list):
            result[key] = list(map(
                lambda x: to_dict(x) if hasattr(x, "to_dict") else x,
                value
            ))
        elif hasattr(value, "to_dict"):
            result[key] = to_dict(value)
        elif isinstance(value, dict):
            result[key] = dict(map(
                lambda item: (item[0], to_dict(item[1]))
                if hasattr(item[1], "to_dict") else item,
                value.items()
            ))
        else:
            result[key] = value

    return result


def to_yaml(resource: object) -> str:
    def remove_none(obj):
        if isinstance(obj, (list, tuple, set)):
            return type(obj)(remove_none(x) for x in obj if x is not None)
        if isinstance(obj, dict):
            return type(obj)((remove_none(k), remove_none(v))
                             for k, v in obj.items() if k is not None and v is not None)
        return obj

    resource_dict = to_dict(resource) if (
                hasattr(resource, "openapi_types") and hasattr(resource, "attribute_map")) else {}
    stream = StringIO()
    yaml.dump(remove_none(resource_dict), stream)
    return stream.getvalue()
