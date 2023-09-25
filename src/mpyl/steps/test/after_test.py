""" After test step. Stops any services running from docker-compose if necessary."""
import os
from logging import Logger

from python_on_whales import DockerClient

from . import STAGE_NAME
from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...utilities.docker import stream_docker_logging


class IntegrationTestAfter(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="After Test",
                description="After test step",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        compose_file = step_input.project.test_containers_path
        if not os.path.exists(compose_file):
            return Output(success=True, message="No containers to stop")

        self._logger.debug(f"Stopping containers in {compose_file}")
        docker_client = DockerClient(compose_files=[compose_file])
        logs = docker_client.compose.logs(stream=True)
        stream_docker_logging(
            logger=self._logger, generator=logs, task_name=f"Stop {compose_file}"
        )

        docker_client.compose.down(remove_orphans=True)
        container_names = list(
            map(lambda l: l.name, docker_client.compose.ps(all=True))
        )

        return Output(success=True, message=f"Stopped {', '.join(container_names)}")
