"""Deploys the Camunda diagrams in the build stage to Camunda cluster, using BPM. """
import os
from logging import Logger
from python_on_whales import docker, Container, DockerException
from ...utilities.docker import execute_with_stream
from ...utilities.bpm import CamundaConfig
from . import STAGE_NAME
from .. import Step, Meta
from ..models import Input, Output, ArtifactType


class BpmnDiagramDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="BPM Diagram Deploy",
                description="Deploy BPMN diagram to Camunda Cluster",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
            # TO DO: make an artifcatype with a camunda deployed diagram link
        )

    def execute(self, step_input: Input) -> Output:
        camunda_config = CamundaConfig.from_config(
            step_input.run_properties.config,
            step_input.run_properties.target,
            step_input.project.root_path,
        )
        volume_path = os.path.join(os.getcwd(), camunda_config.bpm_project_path)
        docker_container = self._get_docker_container(volume_path, camunda_config)
        bpm_file_path = camunda_config.bpm_diagram_folder_path
        try:
            for file_name in (
                [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
                if os.path.isdir(bpm_file_path)
                else []
            ):
                self._logger.info(file_name)
                relative_file_path = os.path.relpath(
                    os.path.join(bpm_file_path, file_name), volume_path
                )
                run_command = f"zbctl deploy {relative_file_path}"
                result = execute_with_stream(
                    logger=self._logger,
                    container=docker_container,
                    command=run_command,
                    task_name=f"Deploy bpmn diagram {file_name}",
                )
                for stdout in result:
                    if "error Command failed with exit code" in stdout:
                        raise DockerException(
                            command_launched=[run_command], return_code=1
                        )
        except DockerException:
            return Output(
                success=False,
                message=f"Deploy BPMN diagrams for project {step_input.project.name} have one or more failures",
                produced_artifact=None,
            )
        finally:
            docker_container.stop()
            docker_container.remove()

        return Output(
            success=True,
            message=f"Deployed all diagrams in {step_input.project.name}",
            produced_artifact=None,
        )

    def _get_docker_container(
        self, volume_path: str, camunda_config: CamundaConfig
    ) -> Container:
        custom_image_tag = "mpyl/bpmn"
        docker.build(
            context_path=volume_path,
            tags=[custom_image_tag],
            file=f"{volume_path}{camunda_config.docker_file_path}",
        )

        docker_container = docker.run(
            image=custom_image_tag,
            interactive=True,
            detach=True,
            volumes=[(volume_path, camunda_config.docker_directory_path)],
            envs={
                "ZEEBE_ADDRESS": camunda_config.cluster_id,
                "ZEEBE_CLIENT_ID": camunda_config.client_id,
                "ZEEBE_CLIENT_SECRET": camunda_config.client_secret,
            },
            workdir=camunda_config.docker_directory_path,
        )
        if not isinstance(docker_container, Container):
            raise TypeError("Docker run command should return a container")

        return docker_container
