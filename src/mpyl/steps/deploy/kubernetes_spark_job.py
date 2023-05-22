""" A step to deploy a job to kubernetes. """

from logging import Logger

from .k8s import deploy_helm_chart
from .k8s.chart import ChartBuilder, to_spark_job_chart
from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage
from ...stages.discovery import find_deploy_set
from ...utilities.repo import RepoConfig


class DeployKubernetesSparkJob(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Spark Job Deploy',
            description='Deploy a Spark Job to the Spark Operator',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        chart = to_spark_job_chart(
            ChartBuilder(step_input, find_deploy_set(RepoConfig(step_input.run_properties.config))))
        return deploy_helm_chart(self._logger, chart, step_input, ChartBuilder(step_input).release_name,
                                 delete_existing=True)
