"""Configuration required for running cypress"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CypressConfig:
    volumePath: str
    record_key: Optional[str]

    @staticmethod
    def from_config(config: dict):
        cypress_config = config.get('cypress')
        if not cypress_config:
            raise KeyError('Cypress section needs to be defined in mpyl_config.yml')

        return CypressConfig(volumePath=cypress_config['volumePath'], record_key=cypress_config['recordKey'])
