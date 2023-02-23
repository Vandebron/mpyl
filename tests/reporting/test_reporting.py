from datetime import datetime

from src.mpyl.project import Project, Stages, Stage
from src.mpyl.reporting.simple import to_string, to_test_report
from src.mpyl.steps.models import Output, Artifact, ArtifactType
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import StepResult
from src.mpyl.utilities.junit import TEST_OUTPUT_PATH_KEY
from tests import root_test_path
from tests.test_resources import test_data
from tests.test_resources.test_data import assert_roundtrip


class TestReporting:
    test_resource_path = root_test_path / "reporting" / "test_resources"

    def test_should_print_results_as_string(self):
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
                                               produced_artifact=Artifact(artifact_type=ArtifactType.JUNIT_TESTS,
                                                                          revision='revision',
                                                                          producing_step='Docker Test', spec={})),
                                 timestamp=datetime.fromisoformat('2019-01-04T16:41:45+02:00')))
        simple_report = to_string(result)
        assert_roundtrip(self.test_resource_path / "simple_run.txt", simple_report)

    def test_should_convert_test_report_to_string(self):
        test_artifact = Artifact(artifact_type=ArtifactType.JUNIT_TESTS, revision='revision',
                                 producing_step='Docker Test',
                                 spec={TEST_OUTPUT_PATH_KEY: self.test_resource_path})
        test_report = to_test_report(test_artifact)
        assert_roundtrip(self.test_resource_path / "simple_test.txt", test_report, overwrite=False)
