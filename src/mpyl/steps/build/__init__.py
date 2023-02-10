from typing import Dict


class DockerConfig:
    host_name: str
    user_name: str
    password: str
    root_folder: str
    build_target: str
    docker_file_name: str

    def __init__(self, config: Dict):
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['host_name']
            self.user_name = registry['user_name']
            self.password = registry['password']
            build: dict = config['docker']['build']
            self.root_folder = build['root_folder']
            self.build_target = build['build_target']
            self.docker_file_name = build['docker_file_name']

        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc
