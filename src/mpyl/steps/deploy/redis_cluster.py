"""A step to deploy a Redis Cluster"""

from logging import Logger

from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage


class RedisClusterDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Redis Cluster Deploy',
            description='Deploy a redis cluster to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        return Output(success=True, message=f"Redis cluster deploy successful for project {step_input.project.name}")
