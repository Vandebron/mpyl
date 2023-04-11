from io import StringIO
from logging import Logger

from ruamel.yaml import YAML

from src.mpyl.steps import Input
from src.mpyl.steps.deploy.redis_cluster import RedisClusterDeploy, compose_values
from tests import test_resource_path, root_test_path
from tests.test_resources.test_data import get_project, RUN_PROPERTIES, assert_roundtrip


class TestRedisStep:

    def test_compose_values(self):
        step_input = Input(get_project(), RUN_PROPERTIES, required_artifact=None, dry_run=True)
        values_path = root_test_path / "steps" / "deploy" / "redis" / "resources"

        yaml_values = compose_values(step_input)
        stream = StringIO()
        YAML().dump(yaml_values, stream)

        assert_roundtrip(values_path / "values.yaml", stream.getvalue())
