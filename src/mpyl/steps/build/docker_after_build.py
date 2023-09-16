""" Pushes the artifact created in the build stage to the docker registry for any build step that has
ArtifactType.DOCKER_IMAGE as `mpyl.steps.models.ArtifactType`."""

from logging import Logger

from .. import Step, Meta
from ..models import Input, Output, Artifact, ArtifactType
from ...project import Stage
from ...utilities.docker import (
    DockerConfig,
    docker_registry_path,
    DockerImageSpec,
    push_to_registry,
)


class AfterBuildDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="After Docker Build",
                description="Push docker image to registry",
                version="0.0.1",
                stage=Stage.BUILD,
            ),
            ArtifactType.DOCKER_IMAGE,
            ArtifactType.DOCKER_IMAGE,
        )

    def execute(self, step_input: Input) -> Output:
        image_name = step_input.as_spec(DockerImageSpec).image
        self._logger.debug(f"Image to publish: {image_name}")

        docker_config = DockerConfig.from_dict(step_input.run_properties.config)

        full_image_path = docker_registry_path(docker_config, image_name)
        artifact = Artifact(
            ArtifactType.DOCKER_IMAGE,
            step_input.run_properties.versioning.revision,
            self.meta.name,
            DockerImageSpec(image=full_image_path),
        )

        if step_input.dry_run:
            return Output(
                success=True,
                message=f"Dry run. Not pushing {image_name} to {docker_config.host_name}",
                produced_artifact=artifact,
            )

        push_to_registry(self._logger, docker_config, image_name)

        return Output(
            success=True,
            message=f"Pushed {full_image_path}",
            produced_artifact=artifact,
        )
