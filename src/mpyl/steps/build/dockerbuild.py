""" Step that builds a docker image from its specification in Dockerfile-mpl. """

from logging import Logger

from .docker_after_build import AfterBuildDocker
from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact
from ...project import Stage
from ...utilities.docker import DockerConfig, build, docker_image_tag, docker_file_path

DOCKER_IGNORE_DEFAULT = ['**/target/*', '**/.mpl/*']


class BuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Build',
            description='Build docker image',
            version='0.0.1',
            stage=Stage.BUILD
        ), produced_artifact=ArtifactType.DOCKER_IMAGE, required_artifact=ArtifactType.NONE,
                         after=AfterBuildDocker(logger=logger))

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig.from_dict(step_input.run_properties.config)
        build_target = docker_config.build_target
        if not build_target:
            raise ValueError('docker.buildTarget must be specified')

        image_tag = docker_image_tag(step_input)
        dockerfile = docker_file_path(project=step_input.project, docker_config=docker_config)

        success = build(logger=self._logger, root_path=docker_config.root_folder,
                        file_path=dockerfile, image_tag=image_tag,
                        target=build_target)
        artifact = input_to_artifact(ArtifactType.DOCKER_IMAGE, step_input, spec={'image': image_tag})

        with open('.dockerignore', 'w+', encoding='utf-8') as ignore_file:
            contents = '\n'.join(DOCKER_IGNORE_DEFAULT)
            ignore_file.write(contents)

        if success:
            return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=artifact)

        return Output(success=False, message=f"Failed to build docker image for {step_input.project.name}",
                      produced_artifact=None)
