""" Step that tests the docker image from the target `tester` in Dockerfile-mpl.


## 🧪 Testing inside a container

When unit tests are run within a docker container the test results need to be written to a folder inside it.
This means that the test step _within the docker container_ should not return a system error.
Otherwise, building of the container would stop and the test results would not be committed to a layer.

The test results need to be writted  written to a folder named `$WORKDIR/target/test-reports/` for
`TestDocker.extract_test_results` to find and extract them.


"""
import shutil
from logging import Logger
from pathlib import Path

from python_on_whales import docker
from python_on_whales.exceptions import NoSuchContainer

from .after_test import IntegrationTestAfter
from .before_test import IntegrationTestBefore
from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact, Artifact
from ...project import Stage, Project
from ...utilities.docker import DockerConfig, build, docker_image_tag, docker_file_path
from ...utilities.junit import to_test_suites, sum_suites, TEST_OUTPUT_PATH_KEY


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        meta = Meta(name='Docker Test', description='Test docker image', version='0.0.1', stage=Stage.TEST)
        super().__init__(
            logger=logger, meta=meta,
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
            before=IntegrationTestBefore(logger),
            after=IntegrationTestAfter(logger)
        )

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig.from_dict(step_input.run_properties.config)
        test_target = docker_config.test_target
        if not test_target:
            raise ValueError('docker.testTarget must be specified')

        tag = docker_image_tag(step_input) + '-test'
        project = step_input.project
        dockerfile = docker_file_path(project=project, docker_config=docker_config)

        success = build(logger=self._logger, root_path=docker_config.root_folder,
                        file_path=dockerfile, image_tag=tag, target=test_target)

        if success:
            artifact = self.extract_test_results(self._logger, project, tag, step_input)

            suite = to_test_suites(artifact)
            summary = sum_suites(suite)

            return Output(success=summary.is_success, message=f"Tests results produced for {project.name} ({summary})",
                          produced_artifact=artifact)

        return Output(success=False,
                      message=f"Tests failed to run for {project.name}. No test results have been recorded.",
                      produced_artifact=None)

    @staticmethod
    def extract_test_results(logger: Logger, project: Project, tag: str, step_input: Input) -> Artifact:
        test_result_path = Path(project.target_path, "test_results")
        shutil.rmtree(test_result_path, ignore_errors=True)
        Path(test_result_path).mkdir(parents=True, exist_ok=True)

        container_id = docker.create(tag).id

        if not docker.container.exists(container_id):
            raise ValueError(f'Container {container_id} with test results does not exist')

        path_in_container = f'/{project.test_report_path}/'
        logger.info(
            f"Copying test results from container {container_id} at "
            f"path {path_in_container} to host at {test_result_path}"
        )
        try:
            docker.copy(f'{container_id}:{path_in_container}.', test_result_path)
        except NoSuchContainer as exc:
            logger.warning(f'Could not find test results in container {tag} at expected location {path_in_container}')
            raise exc

        return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                 spec={TEST_OUTPUT_PATH_KEY: f'{test_result_path}'})
