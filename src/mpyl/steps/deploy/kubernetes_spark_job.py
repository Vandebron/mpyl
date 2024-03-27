"""Deploys a Spark Job to a Kubernetes. Requires google
[spark operator](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator) to be installed.
"""

from logging import Logger

from . import STAGE_NAME
from .k8s import deploy_helm_chart
from .k8s.chart import ChartBuilder, to_spark_job_chart
from .. import Step, Meta
from ..models import Input, Output, ArtifactType


class DeployKubernetesSparkJob(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Kubernetes Spark Job Deploy",
                description="Deploy a Spark Job to the Spark Operator",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    def execute(self, step_input: Input) -> Output:
        builder = ChartBuilder(step_input)
        chart = to_spark_job_chart(builder)
        return deploy_helm_chart(
            self._logger,
            chart,
            step_input,
            ChartBuilder(step_input).release_name,
            delete_existing=True,
        )
