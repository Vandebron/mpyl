import pkgutil

import jsonschema
from jsonschema import RefResolver
from ruamel.yaml import YAML

yaml = YAML()


def validate(values: dict, schema: dict):
    project_schema_string = pkgutil.get_data(__name__, "schema/project.schema.yml")
    if not project_schema_string:
        raise ImportError("'schema/project.schema.yml' was not found in bundle")

    project_schema = yaml.load(project_schema_string.decode('utf-8'))

    def load_schema_from_local(uri):
        if 'project.schema.yml' in uri:
            return project_schema
        return {}

    resolver = RefResolver(referrer=schema, base_uri="", handlers={"": load_schema_from_local})

    jsonschema.validate(values, schema, resolver=resolver)
