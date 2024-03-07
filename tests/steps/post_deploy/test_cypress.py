import logging

import pytest

from src.mpyl.project import Project, Stages, Dependencies
from src.mpyl.project_execution import ProjectExecution
from src.mpyl.steps import postdeploy
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.steps.steps import Steps, ExecutionException
from tests.test_resources import test_data


class TestCypress:
    executor = Steps(
        logger=logging.getLogger(),
        properties=test_data.RUN_PROPERTIES,
        steps_collection=StepsCollection(logging.getLogger()),
    )

    def test_should_check_defined_specs(self):
        stages = Stages.from_config({"postdeploy": "Cypress Test"})
        project = Project(
            name="test",
            description="Test project",
            path="",
            stages=stages,
            maintainer=[],
            docker=None,
            build=None,
            deployment=None,
            dependencies=Dependencies.from_config({"postdeploy": []}),
        )
        with pytest.raises(ExecutionException) as exc_info:
            self.executor.execute(
                stage=postdeploy.STAGE_NAME,
                project_execution=ProjectExecution.always_run(project),
            )

        assert "No cypress specs are defined in the project dependencies" in str(
            exc_info.value
        )
