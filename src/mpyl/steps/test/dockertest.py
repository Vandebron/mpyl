""" Step that tests the docker image from the target `tester` in Dockerfile-mpl.


## 🧪 Testing inside a container

When unit tests are run within a docker container the test results need to be written to a folder inside it.
This means that the test step _within the docker container_ should not return a system error.
Otherwise, building of the container would stop and the test results would not be committed to a layer.

The test results need to be written to a folder named `$WORKDIR/target/test-reports/` for
`TestDocker.extract_test_results` to find and extract them.


"""
from logging import Logger
from typing import cast

from python_on_whales import Container

from . import STAGE_NAME
from .after_test import IntegrationTestAfter
from .before_test import IntegrationTestBefore
from .. import Step, Meta
from ..models import (
    Input,
    Output,
    ArtifactType,
    input_to_artifact,
    Artifact,
)
from ...project import Project
from ...utilities.docker import (
    DockerConfig,
    build,
    docker_image_tag,
    docker_file_path,
    docker_copy,
    remove_container,
    create_container,
    push_to_registry,
    registry_for_project,
    get_default_build_args,
    full_image_path_for_project,
)
from ...utilities.junit import (
    to_test_suites,
    sum_suites,
    JunitTestSpec,
)


class TestDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Docker Test",
                description="Test docker image",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
            before=IntegrationTestBefore(logger),
            after=IntegrationTestAfter(logger),
        )

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig.from_dict(step_input.run_properties.config)
        test_target = docker_config.test_target
        if not test_target:
            raise ValueError("docker.testTarget must be specified")

        tag = docker_image_tag(step_input) + "-test"
        project = step_input.project
        dockerfile = docker_file_path(project=project, docker_config=docker_config)
        docker_registry_config = registry_for_project(docker_config, step_input.project)
        success = build(
            logger=self._logger,
            root_path=docker_config.root_folder,
            file_path=dockerfile,
            image_tag=tag,
            target=test_target,
            registry_config=docker_registry_config,
            build_args=get_default_build_args(
                full_image_path_for_project(step_input),
                step_input.project.maintainer,
                step_input.run_properties.versioning.identifier,
            ),
        )

        if success:
            container = create_container(self._logger, tag)
            artifact = self.extract_test_results(
                self._logger, project, container, step_input
            )
            docker_registry = registry_for_project(docker_config, step_input.project)
            if not step_input.dry_run and docker_registry.cache_from_registry:
                push_to_registry(self._logger, docker_registry, tag)

            suite = to_test_suites(cast(JunitTestSpec, artifact.spec))
            summary = sum_suites(suite)

            output = Output(
                success=summary.is_success,
                message=f"Tests results produced for {project.name} ({summary})",
                produced_artifact=artifact,
            )
            remove_container(self._logger, container)
        else:
            output = Output(
                success=False,
                message=f"Tests failed to run for {project.name}. No test results have been recorded.",
                produced_artifact=None,
            )

        return output

    @staticmethod
    def extract_test_results(
        logger: Logger, project: Project, container: Container, step_input: Input
    ) -> Artifact:
        path_in_container = f"{project.test_report_path}/."
        docker_copy(
            logger=logger,
            container_path=path_in_container,
            dst_path=project.test_report_path,
            container=container,
        )

        return input_to_artifact(
            artifact_type=ArtifactType.JUNIT_TESTS,
            step_input=step_input,
            spec=JunitTestSpec(
                project.test_report_path, step_input.run_properties.details.tests_url
            ),
        )
