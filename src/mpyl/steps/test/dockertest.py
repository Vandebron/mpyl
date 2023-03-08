""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """
import shutil
from logging import Logger
from pathlib import Path

from python_on_whales import docker

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
            artifact = self.extract_test_results(project, tag, step_input)

            suite = to_test_suites(artifact)
            summary = sum_suites(suite)

            return Output(success=summary.is_success, message=f"Tests results produced for {project.name} ({summary})",
                          produced_artifact=artifact)

        return Output(success=False,
                      message=f"Tests failed to run for {project.name}. No test results have been recorded.",
                      produced_artifact=None)

    @staticmethod
    def extract_test_results(project: Project, tag, step_input: Input) -> Artifact:
        test_result_path = Path(project.target_path, "test_results")
        shutil.rmtree(test_result_path, ignore_errors=True)
        Path(test_result_path).mkdir(parents=True, exist_ok=True)

        container_id = docker.create(tag).id
        docker.copy(f'{container_id}:/{project.test_report_path}/.', test_result_path)

        return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                 spec={TEST_OUTPUT_PATH_KEY: f'{test_result_path}'})
