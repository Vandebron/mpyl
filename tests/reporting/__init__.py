from datetime import datetime

from src.mpyl.project import Stages, Project, Stage
from src.mpyl.steps.models import Output, Artifact, ArtifactType
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import StepResult
from src.mpyl.utilities.junit import TEST_OUTPUT_PATH_KEY
from tests import root_test_path
from tests.test_resources import test_data

test_resource_path = root_test_path / "reporting" / "test_resources"


def create_test_result() -> RunResult:
    result = RunResult(run_properties=test_data.RUN_PROPERTIES)
    append_results(result)
    return result


def create_test_result_with_plan() -> RunResult:
    build_projects = [test_data.get_project(), __get_other_project()]
    test_projects = [__get_other_project()]
    run_plan = {
        Stage.BUILD: set(build_projects),
        Stage.TEST: set(test_projects)
    }
    return RunResult(run_properties=test_data.RUN_PROPERTIES, run_plan=run_plan)


def append_results(result: RunResult) -> None:
    other_project = __get_other_project()
    result.append(StepResult(stage=Stage.BUILD, project=test_data.get_project(),
                             output=Output(success=False, message='Build failed'),
                             timestamp=datetime.fromisoformat('2019-01-04T16:41:24+02:00')))
    result.append(StepResult(stage=Stage.BUILD, project=other_project,
                             output=Output(success=True, message='Build successful'),
                             timestamp=datetime.fromisoformat('2019-01-04T16:41:26+02:00')))
    result.append(StepResult(stage=Stage.TEST, project=other_project,
                             output=Output(success=True, message='Tests successful',
                                           produced_artifact=
                                           Artifact(artifact_type=ArtifactType.JUNIT_TESTS, revision='revision',
                                                    producing_step='Docker Test',
                                                    spec={TEST_OUTPUT_PATH_KEY: test_resource_path})),
                             timestamp=datetime.fromisoformat('2019-01-04T16:41:45+02:00')))


def __get_other_project():
    stages = Stages(build=None, test=None, deploy=None, postdeploy=None)
    return Project('test', 'Test project', '', stages, [], None, None)
