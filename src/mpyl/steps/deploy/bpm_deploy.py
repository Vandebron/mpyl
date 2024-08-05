"""Deploys the Camunda diagrams in the build stage to Camunda cluster, using BPM. """

from logging import Logger
from typing import List
from functools import reduce
from .bpm import deploy_to_cluster, deploy_to_modeler
from ...utilities.bpm import CamundaConfig
from . import STAGE_NAME
from .. import Step, Meta
from ..models import Input, Output, ArtifactType


class BpmDiagramDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="BPM Diagram Deploy",
                description="Deploy BPM diagram to Camunda Cluster",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.NONE,
            # TO DO: create bpm artifact:
            # https://vandebron.atlassian.net/browse/BPMN-293
        )

    def execute(self, step_input: Input) -> Output:
        bpm_deploy_results = []
        camunda_config = CamundaConfig.from_config(
            step_input.run_properties,
            step_input.project_execution.project,
        )

        project_name = step_input.project_execution.project.name
        result = deploy_to_cluster(self._logger, project_name, camunda_config)
        bpm_deploy_results.append(result)
        if result.success:
            modeler_result = deploy_to_modeler(
                self._logger, project_name, camunda_config
            )
            bpm_deploy_results.append(modeler_result)
        return self.__evaluate_results(bpm_deploy_results)

    def __evaluate_results(self, results: List[Output]):
        return (
            reduce(
                self.__flatten_result_messages,
                results[1:],
                results[0],
            )
            if len(results) > 1
            else results[0]
        )

    def __flatten_result_messages(self, acc: Output, curr: Output) -> Output:
        return Output(
            success=acc.success and curr.success,
            message=f"{acc.message}\n{curr.message}",
        )
