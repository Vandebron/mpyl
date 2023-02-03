""" This module defines a class named DockerConfig.
The class has three variables: host_name, user_name, and password, each of type str.

The __init__ method takes as input a dictionary config and sets the values of host_name, user_name,
and password based on the values stored in the dictionary.
"""

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
