""" Step that builds a docker image from a project in a multi-project sbt. Assumes that the
[sbt-docker](https://github.com/marcuslonnberg/sbt-docker) plugin is present.
"""

from logging import Logger
from typing import Optional

from .post_docker_build import AfterBuildDocker
from .. import Step, Meta
from . import STAGE_NAME
from ...project import Target
from ...steps.models import (
    ArtifactType,
    Input,
    Output,
    input_to_artifact,
)
from ...utilities.docker import docker_image_tag, DockerImageSpec
from ...utilities.sbt import SbtConfig
from ...utilities.subprocess import custom_check_output


class BuildSbt(Step):
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Sbt Build",
                description="Build sbt project",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.DOCKER_IMAGE,
            required_artifact=ArtifactType.NONE,
            after=AfterBuildDocker(logger=logger),
        )

    def execute(self, step_input: Input) -> Output:
        image_name = docker_image_tag(step_input)
        command = self._construct_sbt_command(step_input, image_name)

        output = custom_check_output(self.logger, command=command)
        artifact = input_to_artifact(
            ArtifactType.DOCKER_IMAGE, step_input, DockerImageSpec(image=image_name)
        )
        if output.success:
            return Output(
                success=True,
                message=f"Built {step_input.project.name}",
                produced_artifact=artifact,
            )

        return Output(
            success=False,
            message=f"Failed to build sbt project for {step_input.project.name}",
            produced_artifact=None,
        )

    @staticmethod
    def _construct_sbt_command(step_input: Input, image_name: str):
        check_fmt: Optional[str] = (
            "scalafmtCheckAll"
            if step_input.run_properties.target == Target.PULL_REQUEST
            else None
        )
        commands: list[str] = [
            command
            for command in [
                f"project {step_input.project.name}",
                f'set docker / imageNames := Seq(ImageName("{image_name}"))',
                check_fmt,
                "docker",
            ]
            if command is not None
        ]
        config = SbtConfig.from_config(config=step_input.run_properties.config)
        command = config.to_command(config.build_with_client, commands)
        return command
