import logging

from mpyl.cli.commands.build.mpyl import run_build
from mpyl.project import Stage
from mpyl.steps.run import RunResult
from mpyl.steps.steps import Steps
from tests.test_resources.test_data import get_minimal_project, RUN_PROPERTIES


class TestBuildCommand:

    def test_run_build_without_plan_should_be_successful(self):
        run_properties = RUN_PROPERTIES
        accumulator = RunResult(run_properties=run_properties)
        executor = Steps(logging.getLogger(), run_properties)
        result = run_build(accumulator, executor, None)
        assert not result.has_results
        assert result.is_success
        assert result.status_line == '🦥 Nothing to do'

    def test_run_build_with_plan_should_execute_successfully(self):
        run_properties = RUN_PROPERTIES

        projects = [get_minimal_project()]
        run_plan = {
            Stage.BUILD(): projects,
            Stage.TEST(): projects,
            Stage.DEPLOY(): projects
        }
        accumulator = RunResult(run_properties=run_properties, run_plan=run_plan)
        executor = Steps(logging.getLogger(), run_properties)
        result = run_build(accumulator, executor, None)
        assert result.has_results
        assert result.is_success
        assert result.status_line == '✅ Successful'

        assert result.exception is None
