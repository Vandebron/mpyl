""" Function used to validate the project.schema.yml against the local schema."""

import pkgutil
from functools import lru_cache

import jsonschema
from jsonschema import RefResolver, Draft7Validator, validators
from ruamel.yaml import YAML

yaml = YAML()


def __load_schema_from_local(local_uri: str):
    project_schema_string = pkgutil.get_data(__name__, f"schema/{local_uri}")
    if not project_schema_string:
        raise ImportError(f"'schema/{local_uri}' was not found in bundle")
    return yaml.load(project_schema_string.decode("utf-8"))


def load_schemas_from_local(local_uris: list[str]):
    return {local_uri: __load_schema_from_local(local_uri) for local_uri in local_uris}


@lru_cache(maxsize=10)
def load_schema(schema_string: str) -> Draft7Validator:
    schema = yaml.load(schema_string)

    local_schema_dictionary = load_schemas_from_local(
        ["project.schema.yml", "k8s_api_core.schema.yml"]
    )

    def load_schema_from_local(uri):
        return next(
            (value for key, value in local_schema_dictionary.items() if key in uri), {}
        )

    resolver = RefResolver(
        referrer=schema, base_uri="", handlers={"": load_schema_from_local}
    )
    all_validators = dict(Draft7Validator.VALIDATORS)
    existing_validator = all_validators["type"]

    def allow_none_validator(validator, types, instance, yaml_schema):
        for field_type in types:
            if field_type is None and instance is None:
                return None

        return existing_validator(validator, types, instance, yaml_schema)

    all_validators["type"] = allow_none_validator
    type_checker = Draft7Validator.TYPE_CHECKER

    extended_validator = validators.extend(
        jsonschema.validators.Draft7Validator,
        validators=all_validators,
        type_checker=type_checker,
    )
    return extended_validator(schema=schema, resolver=resolver)


def validate(values: dict, schema_string: str):
    schema = load_schema(schema_string)
    return schema.validate(values)
