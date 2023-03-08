""" Before test step. Starts docker-compose if necessary."""
import os
import time
from dataclasses import dataclass
from logging import Logger

from python_on_whales import DockerClient, Container
from python_on_whales.components.compose.models import ComposeProject

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage
from ...utilities.docker import stream_docker_logging


@dataclass(frozen=True)
class DockerComposeConfig:
    period_seconds: int
    failure_threshold: int

    @property
    def total_duration(self):
        return self.period_seconds * self.failure_threshold

    @staticmethod
    def from_yaml(config: dict):
        return DockerComposeConfig(period_seconds=int(config['periodSeconds']),
                                   failure_threshold=int(config['failureThreshold']))


class IntegrationTestBefore(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Before Test',
            description='Before test step',
            version='0.0.1',
            stage=Stage.TEST
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        compose_file = step_input.project.test_containers_path
        if not os.path.exists(compose_file):
            return Output(success=True, message='No containers to start')

        compose_config = step_input.run_properties.config.get('docker', {}).get('compose')
        if not compose_config:
            raise KeyError('docker.compose needs to be defined')

        config = DockerComposeConfig.from_yaml(compose_config)

        self._logger.debug(f"Starting containers in {compose_file}")
        docker_client = DockerClient(compose_files=[compose_file])
        docker_client.compose.down(remove_orphans=True)
        docker_client.compose.build()
        docker_client.compose.up(detach=True, color=True, quiet=False)

        goal_reached = False
        logs = docker_client.compose.logs(stream=True)
        stream_docker_logging(logger=self._logger, generator=logs, task_name=f'Start {compose_file}')

        poll = 0
        while not goal_reached:
            proj: ComposeProject = docker_client.compose.ls()[0]
            goal_reached = (proj.created + proj.restarting + proj.exited + proj.paused + proj.dead) == 0
            poll += 1
            if poll >= config.failure_threshold:
                return Output(success=False,
                              message=f"Failed to start services in {compose_file} "
                                      f"within {config.total_duration} seconds.")

            time.sleep(config.period_seconds)
        running_containers: list[Container] = docker_client.compose.ps()
        container_names = list(map(lambda l: l.name, running_containers))

        return Output(success=True, message=f"Started {', '.join(container_names)}")
