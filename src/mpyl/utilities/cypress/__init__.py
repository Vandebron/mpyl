"""Configuration required for running cypress"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CypressConfig:
    cypress_source_code_path: str
    record_key: Optional[str]

    @staticmethod
    def from_config(config: dict):
        cypress_config = config.get('cypress')
        if not cypress_config:
            raise KeyError('Cypress section needs to be defined in mpyl_config.yml')

        return CypressConfig(cypress_source_code_path=cypress_config.get('cypressSourceCodePath'),
                             record_key=cypress_config.get('recordKey'))
