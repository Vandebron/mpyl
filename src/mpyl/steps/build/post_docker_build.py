""" Pushes the artifact created in the build stage to the docker registry for any build step that has
ArtifactType.DOCKER_IMAGE as `mpyl.steps.models.ArtifactType`."""

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, Artifact, ArtifactType
from . import STAGE_NAME
from ...utilities.docker import (
    DockerConfig,
    docker_registry_path,
    DockerImageSpec,
    push_to_registry,
    registry_for_project,
)


class AfterBuildDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="After Docker Build",
                description="Push docker image to registry",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.DOCKER_IMAGE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    def execute(self, step_input: Input) -> Output:
        image_name = step_input.as_spec(DockerImageSpec).image
        self._logger.debug(f"Image to publish: {image_name}")

        properties = step_input.run_properties
        docker_config: DockerConfig = DockerConfig.from_dict(properties.config)
        docker_registry = registry_for_project(
            docker_config, step_input.project_execution.project
        )

        full_image_path = docker_registry_path(docker_registry, image_name)
        artifact = Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE,
            revision=properties.versioning.revision,
            producing_step=self.meta.name,
            spec=DockerImageSpec(image=full_image_path),
            hash=step_input.project_execution.cache_key,
        )

        if step_input.dry_run:
            return Output(
                success=True,
                message=f"Dry run. Not pushing {image_name} to {docker_registry.host_name}",
                produced_artifact=artifact,
            )

        push_to_registry(self._logger, docker_registry, image_name)

        return Output(
            success=True,
            message=f"Pushed {full_image_path}",
            produced_artifact=artifact,
        )
