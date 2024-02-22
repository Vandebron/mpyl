"""Deploys the Camunda diagrams in the build stage to Camunda cluster, using BPM. """
import asyncio
import logging
import os
from logging import Logger
from pyzeebe import ZeebeClient, create_camunda_cloud_channel
from . import STAGE_NAME
from ...project import Target
from .. import Step, Meta
from ..models import Input, Output, ArtifactType


class BpmnDiagramDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="BPMN Diagram Deploy",
                description="Deploy BPMN diagram to Camunda Cluster",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
            # make an artifcatype with a camunda deployed diagram link
        )

    async def __deploy_all_diagrams(
        self, bpm_file_path: str, zeebe_client: ZeebeClient
    ):
        for file_name in (
            [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
            if os.path.isdir(bpm_file_path)
            else []
        ):
            logging.log(logging.INFO, file_name)
            await self.__deploy_diagram(bpm_file_path + file_name, zeebe_client)

    async def __deploy_diagram(self, path: str, zeebe_client: ZeebeClient):
        await zeebe_client.deploy_process(path)

    def __get_env_value(self, target: Target):
        if target == Target.PULL_REQUEST:
            env = "pr"
        elif target == Target.PULL_REQUEST_BASE:
            env = "test"
        elif target == Target.ACCEPTANCE:
            env = "acceptance"
        elif target == Target.PRODUCTION:
            env = "production"
        return env

    def execute(self, step_input: Input) -> Output:
        env = self.__get_env_value(step_input.run_properties.target)
        camunda_config_info = step_input.run_properties.config.get("camunda")
        if camunda_config_info is not None:
            camunda_config = camunda_config_info.get(env)

        channel = create_camunda_cloud_channel(
            client_id=camunda_config.get("clientId"),
            client_secret=camunda_config.get("clientSecret"),
            cluster_id=camunda_config.get("clusterId"),
            region="bru-2",
        )
        zeebe_client = ZeebeClient(channel)
        bpm_file_paths = step_input.project.path + "/src/test/resources/"
        is_success = True

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.__deploy_all_diagrams(bpm_file_paths, zeebe_client)
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            is_success = False
            message = str(exc)
            logging.log(logging.WARNING, message)
        return Output(
            success=is_success,
            message=f"Deployed diagrams in {step_input.project.name}: {message}",
            produced_artifact=None,
        )
