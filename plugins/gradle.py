from logging import Logger
from pathlib import Path

from mpyl.steps import Step, Meta, ArtifactType, Input, Output
from mpyl.steps.models import input_to_artifact, ArchiveSpec
from mpyl.utilities.junit import to_test_suites, sum_suites, JunitTestSpec
from mpyl.utilities.subprocess import custom_check_output


def run_gradle(logger: Logger, target: Path, task: str) -> Output:
    project = str(target).replace("/", ":")
    return custom_check_output(
        logger=logger, command=f"./gradlew {project}:{task} --no-daemon --info"
    )


class BuildGradle(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Gradle Build",
                description="Build a gradle target",
                version="0.0.1",
                stage="build",
            ),
            produced_artifact=ArtifactType.ARCHIVE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        execution = step_input.project_execution
        self._logger.info(f"Building project {execution.name}")
        path = execution.project.root_path

        run_outcome = run_gradle(self._logger, path, "bootJar")

        archive_path = path / "build" / "libs" / f"{path.name}.jar"
        artifact = input_to_artifact(
            ArtifactType.ARCHIVE,
            step_input,
            spec=ArchiveSpec(archive_path=f"{archive_path}"),
        )

        return Output(
            success=run_outcome.success,
            message=f"Built {execution.name}",
            produced_artifact=artifact,
        )


class TestGradle(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Gradle Test",
                description="Test a gradle target",
                version="0.0.1",
                stage="test",
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        execution = step_input.project_execution
        self._logger.info(f"Testing project {execution.name}")
        path = execution.project.root_path

        run_outcome = run_gradle(self._logger, path, "test")

        test_spec = JunitTestSpec(
            test_output_path=f"{step_input.project_execution.project.root_path}build/test-results/test",
            test_results_url=None,
        )
        test_spec.test_results_summary = sum_suites(
            to_test_suites(Path(test_spec.test_output_path))
        )

        artifact = input_to_artifact(
            artifact_type=ArtifactType.JUNIT_TESTS,
            step_input=step_input,
            spec=test_spec,
        )

        return Output(
            success=run_outcome.success,
            message=f"Tested {execution.name}",
            produced_artifact=artifact,
        )
