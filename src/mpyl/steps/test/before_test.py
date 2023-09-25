""" Before test step. Starts docker-compose if necessary."""
import os
import time
from dataclasses import dataclass
from logging import Logger

from python_on_whales import DockerClient, Container
from python_on_whales.components.compose.models import ComposeProject
from python_on_whales.components.container.models import ContainerHealthcheckResult

from . import STAGE_NAME
from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...utilities.docker import stream_docker_logging, DockerComposeConfig


@dataclass(frozen=True)
class ContainerHealth:
    name: str
    status: str
    health_checks: list[ContainerHealthcheckResult]


class IntegrationTestBefore(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Before Test",
                description="Before test step",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    @staticmethod
    def all_running(project_status: ComposeProject):
        total_not_running: int = (
            (project_status.created or 0)
            + (project_status.restarting or 0)
            + (project_status.exited or 0)
            + (project_status.paused or 0)
            + (project_status.dead or 0)
        )
        return total_not_running == 0

    def execute(self, step_input: Input) -> Output:
        compose_file = step_input.project.test_containers_path
        if not os.path.exists(compose_file):
            return Output(success=True, message="No containers to start")

        config = DockerComposeConfig.from_yaml(step_input.run_properties.config)

        self._logger.debug(f"Starting containers in {compose_file}")
        docker_client = DockerClient(compose_files=[compose_file])
        docker_client.compose.down(remove_orphans=True)
        docker_client.compose.build()
        docker_client.compose.up(detach=True, color=True, quiet=False)

        goal_reached: bool = False
        logs = docker_client.compose.logs(stream=True)
        stream_docker_logging(
            logger=self._logger, generator=logs, task_name=f"Start {compose_file}"
        )

        poll = 0
        while not goal_reached:
            project_status: ComposeProject = docker_client.compose.ls()[0]
            containers = docker_client.compose.ps()
            container_healths = [
                ContainerHealth(c.name, c.state.health.status, c.state.health.log or [])
                for c in containers
                if c.state.health is not None and c.state.health.status is not None
            ]
            all_healthy = all(
                container.status == "healthy" for container in container_healths
            )

            goal_reached = self.all_running(project_status) and all_healthy

            unhealthy = [
                (c.name, c.status, c.health_checks)
                for c in container_healths
                if c.status != "healthy"
            ]
            if not goal_reached:
                if poll == 0:
                    self._logger.info(
                        "Waiting for container to be running and healthy.."
                    )
                self._logger.debug(f"Project stats: {project_status}")
                self._logger.debug(f"Container healths: {unhealthy}")

            poll += 1
            if poll >= config.failure_threshold:
                if unhealthy:
                    self._logger.info(f"Unhealthy containers: {unhealthy}")
                return Output(
                    success=False,
                    message=f"Failed to start services in {compose_file} "
                    f"within {config.total_duration} seconds.",
                )

            time.sleep(config.period_seconds)
        running_containers: list[Container] = docker_client.compose.ps()
        container_names = list(map(lambda l: l.name, running_containers))

        return Output(success=True, message=f"Started {', '.join(container_names)}")
