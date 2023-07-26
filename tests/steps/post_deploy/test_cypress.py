import logging

import pytest

from src.mpyl.project import Project, Stages, Stage, Dependencies
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.steps.steps import Steps, ExecutionException
from tests.test_resources import test_data


class TestCypress:
    executor = Steps(
        logger=logging.getLogger(),
        properties=test_data.RUN_PROPERTIES,
        steps_collection=StepsCollection(logging.getLogger(), "src"),
    )

    def test_should_check_defined_specs(self):
        stages = Stages.from_config({"postdeploy": "Cypress Test"})
        project = Project(
            name="test",
            description="Test project",
            path="",
            stages=stages,
            maintainer=[],
            deployment=None,
            dependencies=Dependencies.from_config({"postdeploy": []}),
        )

        with pytest.raises(ExecutionException) as exc_info:
            self.executor.execute(stage=Stage.POST_DEPLOY, project=project)

        assert "No cypress specs are defined in the project dependencies" in str(
            exc_info.value
        )
