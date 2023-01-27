from typing import Dict


class DockerConfig:
    host_name: str
    user_name: str
    password: str

    def __init__(self, config: Dict):
        try:
            registry: dict = config['docker']['registry']
            self.host_name = registry['host_name']
            self.user_name = registry['user_name']
            self.password = registry['password']
        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc
