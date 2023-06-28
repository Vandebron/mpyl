import logging

from src.mpyl.cli.commands.build.mpyl import run_build
from src.mpyl.project import Stage
from src.mpyl.steps import Step, Meta, ArtifactType, Input, Output
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps, StepsCollection
from tests.test_resources.test_data import (
    get_minimal_project,
    RUN_PROPERTIES,
    get_project_with_stages,
)


class ThrowingStep(Step):
    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Throwing Build",
                description="Throwing build step to validate error handling",
                version="0.0.1",
                stage=Stage.BUILD,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:
        raise Exception("this is not good")


class TestBuildCommand:
    def test_run_build_without_plan_should_be_successful(self):
        run_properties = RUN_PROPERTIES
        accumulator = RunResult(run_properties=run_properties)
        executor = Steps(
            logging.getLogger(),
            run_properties,
            StepsCollection(logging.getLogger(), "src"),
        )
        result = run_build(accumulator, executor, None)
        assert not result.has_results
        assert result.is_success
        assert result.status_line == "🦥 Nothing to do"

    def test_run_build_with_plan_should_execute_successfully(self):
        run_properties = RUN_PROPERTIES

        projects = [get_minimal_project()]
        run_plan = {Stage.BUILD: projects, Stage.TEST: projects, Stage.DEPLOY: projects}
        accumulator = RunResult(run_properties=run_properties, run_plan=run_plan)
        executor = Steps(
            logging.getLogger(),
            run_properties,
            StepsCollection(logging.getLogger(), "src"),
        )
        result = run_build(accumulator, executor, None)
        assert result.exception is None
        assert result.status_line == "✅ Successful"
        assert result.is_success

        assert result.exception is None

    def test_run_build_throwing_step_should_be_handled(self):
        run_properties = RUN_PROPERTIES

        projects = [get_project_with_stages({"build": "Throwing Build"})]
        run_plan = {Stage.BUILD: projects}
        accumulator = RunResult(run_properties=run_properties, run_plan=run_plan)
        logger = logging.getLogger()
        collection = StepsCollection(logger, "src")
        executor = Steps(logger, run_properties, collection)

        result = run_build(accumulator, executor, None)
        assert not result.has_results
        assert result.status_line == "❗ Failed with exception"

        assert result.exception.message == "this is not good"
        assert result.exception.stage == Stage.BUILD.name
        assert result.exception.project_name == "test"
        assert result.exception.executor == "Throwing Build"
