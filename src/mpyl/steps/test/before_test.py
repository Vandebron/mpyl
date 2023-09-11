""" Before test step. Starts docker-compose if necessary."""
import os
import time
from logging import Logger

from python_on_whales import DockerClient, Container
from python_on_whales.components.compose.models import ComposeProject

from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...project import Stage
from ...utilities.docker import stream_docker_logging, DockerComposeConfig


class IntegrationTestBefore(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Before Test",
                description="Before test step",
                version="0.0.1",
                stage=Stage.TEST,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

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
            proj: ComposeProject = docker_client.compose.ls()[0]
            state = docker_client.compose.ps()[0].state
            total_not_running: int = (
                (proj.created or 0)
                + (proj.restarting or 0)
                + (proj.exited or 0)
                + (proj.paused or 0)
                + (proj.dead or 0)
            )
            healthy: bool = (
                state.health is not None
                and state.health.status is not None
                and state.health.status == "healthy"
            )
            goal_reached = total_not_running == 0 and healthy

            if not goal_reached:
                self._logger.info("Waiting for container to be running and healthy..")
                self._logger.debug(f"Project stats: {proj}")
                self._logger.debug(f"Container state: {state}")

            poll += 1
            if poll >= config.failure_threshold:
                return Output(
                    success=False,
                    message=f"Failed to start services in {compose_file} "
                    f"within {config.total_duration} seconds.",
                )

            time.sleep(config.period_seconds)
        running_containers: list[Container] = docker_client.compose.ps()
        container_names = list(map(lambda l: l.name, running_containers))

        return Output(success=True, message=f"Started {', '.join(container_names)}")
