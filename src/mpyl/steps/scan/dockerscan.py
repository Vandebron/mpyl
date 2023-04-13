""" Step that scans the docker image from the target `scanner` in Dockerfile-mpl. """

from logging import Logger

from mpyl.steps import Step, Meta
from mpyl.steps.models import Input, Output, ArtifactType
from mpyl.project import Stage
from mpyl.utilities.docker import DockerConfig, build, docker_image_tag, docker_file_path


class ScanDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Docker Scan',
            description='Docker scan step to check vulnerabilities.',
            version='0.0.1',
            stage=Stage.TEST
        ), ArtifactType.NONE, ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig.from_dict(step_input.run_properties.config)
        tag = docker_image_tag(step_input) + '-scan'
        project = step_input.project
        dockerfile = docker_file_path(project=project, docker_config=docker_config)

        success = build(logger=self._logger, root_path=docker_config.root_folder,
                        file_path=dockerfile, image_tag=tag, target='scanner')
        if success:
            return Output(success=True, message=f"Successful vulnerability scan of container for {project.name})")

        return Output(success=False, message=f"Vulnerability scan failed for {project.name}. Please check the logs "
                                             f"for further info and update your base image/other dependencies")
