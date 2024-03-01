"""Configuration required for running bpmn"""
import uuid
import logging
import sys
from dataclasses import dataclass
from typing import Optional
from ...project import Target, TargetProperty


@dataclass(frozen=True)
class CamundaConfig:
    cluster_id: str
    client_id: str
    client_secret:str
    
    @staticmethod
    def from_config(config: dict, target: Target):
        camunda_config: dict = config.get("camunda")
        if not camunda_config:
            raise KeyError("Camunda section needs to be defined in mpyl_config.yml")
        
        config = TargetProperty.from_config(camunda_config).get_value(target)

        return CamundaConfig(
            cluster_id=config.get("clusterId"),
            client_id=config.get("clientId"),
            client_secret=config.get("clientSecret")
        )
        
        
