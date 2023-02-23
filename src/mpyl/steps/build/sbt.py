import subprocess
from logging import Logger
from typing import Optional

from .. import Target
from ..step import Step
from ...project import Stage
from ...steps.models import Meta, ArtifactType, Input, Output, input_to_artifact
from ...utilities.docker import docker_image_tag
from ...utilities.sbt import SbtConfig


class BuildSbt(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name='Sbt Build',
                description='Build sbt project',
                version='0.0.1',
                stage=Stage.BUILD
            ),
            produced_artifact=ArtifactType.DOCKER_IMAGE,
            required_artifact=ArtifactType.NONE,
            after=None  # AfterBuildDocker(logger=logger)
        )

    def execute(self, step_input: Input) -> Output:
        with open(SbtConfig.java_opts_file_name, 'r') as jvm_opts:
            jvm_opts.write(SbtConfig.sbt_opts.replace(' ', '\n'))
            check_fmt: Optional[str] = \
                'scalafmtCheckAll' if step_input.run_properties.target == Target.PULL_REQUEST else None
            image_name: str = docker_image_tag(step_input)
            commands: list[str] = [
                command for command in [
                    f'project {step_input.project.name}',
                    f'set docker / imageNames := Seq(ImageName("${image_name}"))',
                    check_fmt,
                    'docker'
                ] if command is not None
            ]
            try:
                subprocess.run(f'{SbtConfig.sbt_command} {"; ".join(commands)}', check=True)
                artifact = input_to_artifact(ArtifactType.DOCKER_IMAGE, step_input, {'image': image_name})
                return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=artifact)
            except subprocess.CalledProcessError:
                return Output(success=False, message=f"Failed to build sbt project for {step_input.project.name}",
                              produced_artifact=None)
