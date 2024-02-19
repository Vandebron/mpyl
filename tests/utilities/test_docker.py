from src.mpyl.utilities.docker import (
    DockerConfig,
    docker_registry_path,
    ecr_repository_path,
    registry_for_project,
)

from tests.test_resources.test_data import get_config_values, get_project


class TestDocker:
    def test_registry_path(self):
        config_values = get_config_values()
        conf = DockerConfig.from_dict(config_values)
        default_registry = registry_for_project(conf, get_project())
        assert default_registry.host_name == "docker_host"
        assert default_registry.organization is None
        assert docker_registry_path(default_registry, "image") == "docker_host/image"

    def test_ecr_repository_path(self):
        config_values = get_config_values()
        conf = DockerConfig.from_dict(config_values)
        default_registry = registry_for_project(conf, get_project())
        host_name = f"{default_registry}/repo/project"
        assert ecr_repository_path(host_name, "JOB:pr-392") == "repo/project/job"
