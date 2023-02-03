"""This file defines a class BuildDocker which is a subclass of the Step class. This class implements a step for
building a Docker image for a project. The execute method uses the Docker APIClient to build the image and log the
build output. The BuildDocker class is defined as a build stage step with a name "Docker Build", a description "Build
docker image", and a version "0.0.1". The class specifies that the output artifact produced is a Docker image,
and that no input artifact is required. The class also has "after" step, which calls an instance of the
AfterBuildDocker class, that pushes the image to the docker registry.
"""

from logging import Logger

from docker import APIClient  # type: ignore

from .docker_after_build import AfterBuildDocker
from ..models import Meta, Input, Output, Artifact, ArtifactType
from ..step import Step
from ...stage import Stage


class BuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Build',
            description='Build docker image',
            version='0.0.1',
            stage=Stage.BUILD
        ), produced_artifact=ArtifactType.DOCKER_IMAGE, required_artifact=ArtifactType.NONE,
                         after=AfterBuildDocker(logger=logger))

    def __log_docker_output(self, generator, task_name: str = 'docker command execution') -> None:
        while True:
            try:
                output = next(generator)
                if 'stream' in output:
                    output_str = output['stream'].strip('\n')
                    self._logger.info(output_str)
            except StopIteration:
                self._logger.info(f'{task_name} complete.')
                break

    def execute(self, step_input: Input) -> Output:
        project = step_input.project
        self._logger.info(f"Building project {project.name}")
        low_level_client = APIClient()
        self._logger.debug(low_level_client.version())

        logs = low_level_client.build(path=project.deployment_path, dockerfile='Dockerfile-mpl',
                                      tag=step_input.docker_image_tag(),
                                      rm=True, target="installer", decode=True)
        self.__log_docker_output(logs)

        artifact = Artifact(ArtifactType.DOCKER_IMAGE, step_input.build_properties.versioning.revision, self.meta.name,
                            {'image': step_input.docker_image_tag()})
        return Output(success=True, message=f"Built {step_input.project.name}", produced_artifact=artifact)
