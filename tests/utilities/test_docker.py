from src.mpyl.utilities.docker import DockerConfig, docker_registry_path

from tests.test_resources.test_data import get_config_values


class TestDocker:
    def test_registry_path(self):
        config_values = get_config_values()
        conf = DockerConfig.from_dict(config_values)
        assert conf.host_name == "docker_host"
        assert conf.organization is None
        assert docker_registry_path(conf, "image") == "docker_host/image"
