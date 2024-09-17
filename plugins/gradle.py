from logging import Logger

from src.mpyl.steps import Step, Meta, ArtifactType, Input, Output
from src.mpyl.steps.models import input_to_artifact, ArchiveSpec
from src.mpyl.utilities.subprocess import custom_check_output


def run_gradle(logger: Logger, target: str, task: str) -> Output:
    return custom_check_output(
        logger=logger,
        command=f"./gradlew {target}:{task} --no-daemon -PmavenUser=$MAVEN_USER -PmavenPassword=$MAVEN_PASSWORD --info",
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
        name = execution.name
        self._logger.info(f"Building project {name}")
        path = execution.project.root_path
        project_name = str(path).replace("/", ":")

        run_outcome = run_gradle(self._logger, project_name, "bootJar")

        archive_path = path / "build" / "libs" / f"{path.name}.jar"
        artifact = input_to_artifact(
            ArtifactType.ARCHIVE,
            step_input,
            spec=ArchiveSpec(archive_path=f"{archive_path}"),
        )

        return Output(
            success=run_outcome.success,
            message=f"Built {name}",
            produced_artifact=artifact,
        )
