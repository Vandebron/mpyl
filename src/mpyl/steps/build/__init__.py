"""
Step implementations relating to the `Build` Stage. These steps produce Docker images by default
"""

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
            self.host_name = registry['hostName']
            self.user_name = registry['userName']
            self.password = registry['password']
            build: dict = config['docker']['build']
            self.root_folder = build['rootFolder']
            self.build_target = build['buildTarget']
            self.docker_file_name = build['dockerFileName']

        except KeyError as exc:
            raise KeyError(f'Docker config could not be loaded from {config}') from exc
