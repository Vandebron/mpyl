"""Deploys the Camunda diagrams in the build stage to Camunda cluster, using BPM. """
import asyncio
import logging
import sys
import os
from logging import Logger
from pyzeebe import ZeebeClient, create_camunda_cloud_channel, create_insecure_channel
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
            required_artifact=ArtifactType.NONE,
            # TO DO: make an artifcatype with a camunda deployed diagram link -> miss information to construct dynamic link...
        )

    async def deploy_all_diagrams(
        self, camunda_config, bpm_file_path: str
    ):
        self._logger.debug(bpm_file_path)
        zeebe_client = self.authentication(camunda_config)
        for file_name in (
            [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
            if os.path.isdir(bpm_file_path)
            else []
        ):
            self._logger.info(file_name)
            await self.deploy_diagram(bpm_file_path + file_name, zeebe_client)

    async def deploy_diagram(self, path: str, zeebe_client: ZeebeClient):
        await zeebe_client.deploy_process(path)
    
    def authentication(self, camunda_config):
        channel = create_insecure_channel(hostname="localhost", port=26500)
        # channel = create_camunda_cloud_channel(
        #         client_id=camunda_config.get("clientId"),
        #         client_secret=camunda_config.get("clientSecret"),
        #         cluster_id=camunda_config.get("clusterId"),
        #         region="bru-2",
        #     )
        return ZeebeClient(channel)

    def get_env_value(self, target: Target):
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
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)
        self._logger = logger
        self._logger.debug(__name__)
        
        env = self.get_env_value(step_input.run_properties.target)
        camunda_config_info = step_input.run_properties.config.get("camunda")
        
        if camunda_config_info is not None:
            camunda_config = camunda_config_info.get(env)
            
        bpm_file_paths = step_input.project.root_path + "src/test/resources/"
        
        try:
            asyncio.run(self.deploy_all_diagrams(camunda_config, bpm_file_paths))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            message = str(exc)
            logger.debug(message)
            return Output(
                success=False,
                message= f"Deployed failed with error {message}",
                produced_artifact=None,
            )
        
        return Output(
            success=True,
            message=f"Deployed all diagrams in {step_input.project.name}",
            produced_artifact=None,
        )
