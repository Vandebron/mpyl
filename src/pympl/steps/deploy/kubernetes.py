from logging import Logger
from pathlib import Path

from .k8s.service import ServiceDeployment, to_yaml
from ..models import Meta, Input, Output, ArtifactType
from ..step import Step
from ...stage import Stage
from pyhelm.chartbuilder import ChartBuilder
from pyhelm.tiller import Tiller


class DeployKubernetes(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Deploy',
            description='Deploy to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        self._logger.info(f"Deploying project {step_input.project.name}")

        dep = ServiceDeployment(step_input)

        templates = dep.to_chart()

        chart_path = Path(step_input.project.target_path) / "chart" / "templates"
        Path(chart_path).mkdir(parents=True, exist_ok=True)

        for k, v in templates.items():
            with open(chart_path / str(k), mode='w+') as file:
                file.write(v)

        chart = ChartBuilder({"name": step_input.project.name, "source": {"type": "directory", "location": chart_path}})

        self._logger.info(chart.dump())

        return Output(success=True, message=f"Deployed project {step_input.project.name}")
