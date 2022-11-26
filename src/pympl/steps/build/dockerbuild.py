from logging import Logger

from docker import APIClient  # type: ignore

from ..models import Meta, Input, Output
from ..step import Step
from ...project import Project
from ...stage import Stage


class BuildDocker(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Docker Build',
            description='Build docker image and push to registry',
            version='0.0.1',
            stage=Stage.BUILD
        ))

    def __log_docker_output(self, generator, task_name: str = 'docker command execution') -> None:
        while True:
            try:
                output = generator.__next__()
                if 'stream' in output:
                    output_str = output['stream'].strip('\n')
                    self._logger.info(output_str)
            except StopIteration:
                self._logger.info(f'{task_name} complete.')
                break

    def execute(self, build_input: Input) -> Output:
        project = build_input.project
        self._logger.info(f"Building project {project.name}")
        low_level_client = APIClient()
        self._logger.debug(low_level_client.version())

        path = Project.to_deployment_path(project.path)
        logs = low_level_client.build(path=path, dockerfile='Dockerfile-mpl', tag=build_input.docker_image_tag(),
                                      rm=True, target="installer", decode=True)
        self.__log_docker_output(logs)

        return Output(success=True, message=f"Built {build_input.project.name}")
