from datetime import datetime

from src.mpyl.project import Stages, Project
from src.mpyl.steps.deploy.k8s import DeployedHelmAppSpec
from src.mpyl.steps.models import (
    Output,
    Artifact,
    ArtifactType,
    RunProperties,
)
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import StepResult
from src.mpyl.utilities.junit import JunitTestSpec
from tests import root_test_path
from tests.test_resources import test_data
from tests.test_resources.test_data import TestStage, properties_values, config_values

test_resource_path = root_test_path / "reporting" / "formatting" / "test_resources"


def create_test_result() -> RunResult:
    result = RunResult(run_properties=test_data.RUN_PROPERTIES)
    append_results(result)
    return result


def create_test_result_with_plan() -> RunResult:
    build_projects = [test_data.get_project(), __get_other_project()]
    test_projects = [__get_other_project()]
    deploy_projects = [__get_other_project()]
    run_plan = {
        TestStage.build(): set(build_projects),
        TestStage.test(): set(test_projects),
        TestStage.deploy(): set(deploy_projects),
    }
    run_properties = RunProperties.from_configuration(
        properties_values, config_values, run_plan
    )
    return RunResult(
        run_properties=run_properties,
    )


def append_results(result: RunResult) -> None:
    other_project = __get_other_project()
    result.append(
        StepResult(
            stage=TestStage.build(),
            project=test_data.get_project(),
            output=Output(success=False, message="Build failed"),
            timestamp=datetime.fromisoformat("2019-01-04T16:41:24+02:00"),
        )
    )
    result.append(
        StepResult(
            stage=TestStage.build(),
            project=other_project,
            output=Output(success=True, message="Build successful"),
            timestamp=datetime.fromisoformat("2019-01-04T16:41:26+02:00"),
        )
    )
    result.append(
        StepResult(
            stage=TestStage.test(),
            project=other_project,
            output=Output(
                success=True,
                message="Tests successful",
                produced_artifact=Artifact(
                    artifact_type=ArtifactType.JUNIT_TESTS,
                    revision="revision",
                    producing_step="Docker Test",
                    spec=JunitTestSpec(
                        str(test_resource_path), "http://localhost/tests"
                    ),
                ),
            ),
            timestamp=datetime.fromisoformat("2019-01-04T16:41:45+02:00"),
        )
    )
    result.append(
        StepResult(
            stage=TestStage.deploy(),
            project=other_project,
            output=Output(
                success=True,
                message="Deploy successful",
                produced_artifact=Artifact(
                    artifact_type=ArtifactType.DEPLOYED_HELM_APP,
                    revision="revision",
                    producing_step="Kubernetes Deploy",
                    spec=DeployedHelmAppSpec(url="https://some.location.com"),
                ),
            ),
            timestamp=datetime.fromisoformat("2019-01-04T16:41:45+02:00"),
        )
    )


def __get_other_project():
    stages = Stages(build=None, test=None, deploy=None, postdeploy=None)
    return Project("test", "Test project", "", stages, [], None, None, None, None)
