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

    stages = Stages(build=None, test=None, deploy=None, postdeploy=None)
    other_project = Project('test', 'Test project', '', stages, [], None, None)

    result.append(StepResult(stage=Stage.BUILD, project=test_data.get_project(),
                             output=Output(success=True, message='Build sucessful'),
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
    return result
