from logging import Logger

from src.mpyl.steps import Step, Meta, ArtifactType, Input, Output
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
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        execution = step_input.project_execution
        name = execution.name
        self._logger.info(f"Building project {name}")
        project_name = str(execution.project.root_path).replace("/", ":")

        run_outcome = run_gradle(self._logger, project_name, "bootJar")

        return Output(
            success=run_outcome.success, message=f"Built {name}", produced_artifact=None
        )
