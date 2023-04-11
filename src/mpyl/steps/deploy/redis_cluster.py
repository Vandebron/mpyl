"""A step to deploy a Redis Cluster"""

from logging import Logger

from .k8s import deploy_external_helm_chart
from .k8s.chart import ChartBuilder
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage


def compose_values(step_input):
    builder = ChartBuilder(step_input)
    cluster_name = builder.release_name
    return {
        'existingSecret': f"{cluster_name}-redis-password",
        'existingSecretPasswordKey': 'password',
        'persistence': {'size': '1Gi'},
        'cluster': {
            'nodes': 3,
            'replicas': 0,
        },
        'metrics': {
            'enabled': True,
            'serviceMonitor': {
                'enabled': True,
                'extraArgs': {
                    'skip-tls-verification': True,
                }
            }
        },
        'image': {
            'tag': '7.0.8'
        },
        'tls': {
            'enabled': True,
            'authClients': False,
            'existingSecret': f'{cluster_name}-redis-cert',
            'certFilename': "tls.crt",
            'certKeyFilename': "tls.key",
            'certCAFilename': "ca.crt"
        }
    }


class RedisClusterDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Redis Cluster Deploy',
            description='Deploy a redis cluster to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        values = compose_values(step_input)
        builder = ChartBuilder(step_input)
        return deploy_external_helm_chart(self._logger, values, step_input, builder.release_name, 'redis-cluster',
                                          'https://charts.bitnami.com/bitnami/', '8.3.11')
