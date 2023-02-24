""" Step that tests the docker image from the target `tester` in Dockerfile-mpl. """
import shutil
import tarfile
from logging import Logger
from pathlib import Path

from docker import APIClient

from ..models import Meta, Input, Output, ArtifactType, input_to_artifact, Artifact
from ..step import Step
from ...utilities.docker import DockerConfig, build, docker_image_tag, docker_file_path
from ...project import Stage, Project
from ...utilities.junit import to_test_suites, sum_suites, TEST_OUTPUT_PATH_KEY


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(logger=logger, meta=Meta(
            name='Docker Test',
            description='Test docker image',
            version='0.0.1',
            stage=Stage.TEST
        ), produced_artifact=ArtifactType.JUNIT_TESTS, required_artifact=ArtifactType.NONE)

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig(step_input.run_properties.config)
        test_target = docker_config.test_target
        if not test_target:
            raise ValueError('docker.testTarget must be specified')

        tag = docker_image_tag(step_input) + '-test'
        project = step_input.project
        dockerfile = docker_file_path(project=project, docker_config=docker_config)

        client: APIClient = APIClient()

        success = build(logger=self._logger, docker_client=client, root_path=docker_config.root_folder,
                        file_path=dockerfile, image_tag=tag, target=test_target)

        if success:
            artifact = self.extract_test_results(self._logger, client, project, tag, step_input)

            suite = to_test_suites(artifact)
            summary = sum_suites(suite)

            return Output(success=summary.is_success, message=f"Tests results produced for {project.name} ({summary})",
                          produced_artifact=artifact)

        return Output(success=False,
                      message=f"Tests failed to run for {project.name}. No test results have been recorded.",
                      produced_artifact=None)

    @staticmethod
    def extract_test_results(logger: Logger, client: APIClient, project: Project, tag, step_input: Input) -> Artifact:
        test_result_path = Path(project.target_path, "test_results")
        shutil.rmtree(test_result_path, ignore_errors=True)
        Path(test_result_path).mkdir(parents=True, exist_ok=True)
        tar_path: Path = test_result_path / 'test_results.tar'

        container_id = client.create_container(tag)
        bits, stat = client.get_archive(container_id, project.test_report_path)
        logger.debug(f"Stats for {tar_path}: {stat}")

        with open(tar_path, mode='wb+') as file:
            for chunk in bits:
                file.write(chunk)
        with tarfile.open(tar_path) as tar_file:
            tar_file.extractall(path=test_result_path)

        return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                                 spec={TEST_OUTPUT_PATH_KEY: f'{test_result_path}/test-reports'})
