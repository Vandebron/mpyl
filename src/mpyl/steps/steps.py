""" Entry point of MPyL. Loads all available Step implementations and triggers their execution based on the specified
Project and Stage.
"""
# import os
# import importlib
import itertools
import pkgutil
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Optional
from unittest import TestSuite

from ruamel.yaml import YAML  # type: ignore

from . import Step
from .build.dockerbuild import BuildDocker # pylint: disable=unused-import
from .build.echo import BuildEcho # pylint: disable=unused-import
from .build.sbt import BuildSbt # pylint: disable=unused-import
from .deploy.echo import DeployEcho # pylint: disable=unused-import
from .deploy.ephemeral_docker_deploy import EphemeralDockerDeploy # pylint: disable=unused-import
from .deploy.kubernetes import DeployKubernetes # pylint: disable=unused-import
from .deploy.kubernetes_job import DeployKubernetesJob # pylint: disable=unused-import
from .deploy.kubernetes_spark_job import DeployKubernetesSparkJob # pylint: disable=unused-import
from .test.dockertest import TestDocker # pylint: disable=unused-import
from .test.echo import TestEcho # pylint: disable=unused-import
from .test.sbt import TestSbt # pylint: disable=unused-import
from .models import Output, Input, RunProperties, ArtifactType, Artifact
from ..project import Project
from ..project import Stage
from ..utilities.junit import to_test_suites
from ..validation import validate

yaml = YAML()


@dataclass(frozen=True)
class StepResult:
    stage: Stage
    project: Project
    output: Output
    timestamp: datetime = datetime.now()


def collect_test_results(step_results: list[StepResult]) -> list[TestSuite]:
    test_artifacts = [res.output.produced_artifact for res in step_results if
                      (res.output.produced_artifact and
                       res.output.produced_artifact.artifact_type == ArtifactType.JUNIT_TESTS)]

    suites: list[list[TestSuite]] = list(map(to_test_suites, test_artifacts))
    return list(itertools.chain(*suites))


class Steps:
    """ Executor of individual steps within a pipeline. """
    _step_executors: dict[Stage, set[Step]]
    _logger: Logger
    _properties: RunProperties

    def __init__(self, logger: Logger, properties: RunProperties) -> None:
        schema_dict = pkgutil.get_data(__name__, "../schema/mpyl_config.schema.yml")

        if schema_dict:
            validate(properties.config, schema_dict.decode('utf-8'))

        self._logger = logger
        self._step_executors: dict[Stage, set[Step]] = {}

        # root_dir =  "src/mpyl/steps/"
        # for drc in os.listdir(root_dir):
        #     if os.path.isdir(os.path.join(root_dir, drc)) and drc != "__pycache__":
        #         files = os.listdir(os.path.join(root_dir, drc))
        #         for file in files:
        #             if file != "__init__.py":
        #                 try:
        #                     importlib.import_module("."+drc+"."+file[:-3], package="src.mpyl.steps")
        #                 except ImportError as exc:
        #                     raise ImportError(f'Could not import {file[:-3]} from {drc}') from exc

        for stage in Stage:
            steps = set()
            for step in Step.get_subclasses():
                if str(stage.name.lower()) in str(step):
                    steps.add(step(logger))
            self._step_executors[stage] = steps

        self._properties = properties

        for stage, steps in self._step_executors.items():
            self._logger.debug(f"Registered executors for stage {stage.name}: "  # pylint: disable=E1101
                  f"{[step.meta.name for step in steps]}")  # pylint: disable=E1101

    def _find_executor(self, stage: Stage, step_name: str) -> Optional[Step]:
        executors = filter(lambda e: e.meta.stage == stage and step_name == e.meta.name, self._step_executors[stage])
        return next(executors, None)

    def _execute(self, executor: Step, project: Project, properties: RunProperties,
                 artifact: Optional[Artifact], dry_run: bool = False) -> Output:
        result = executor.execute(Input(project, properties, required_artifact=artifact, dry_run=dry_run))
        if result.success:
            self._logger.info(
                f"Execution of {executor.meta.name} succeeded for '{project.name}' with outcome '{result.message}'")
        else:
            self._logger.warning(
                f"Execution of {executor.meta.name} failed for '{project.name}' with outcome '{result.message}'")
        return result

    @staticmethod
    def _find_required_artifact(project: Project, required_artifact: Optional[ArtifactType]) -> Optional[Artifact]:
        if not required_artifact or required_artifact == ArtifactType.NONE:
            return None

        for stage in Stage:
            output: Optional[Output] = Output.try_read(project.target_path, stage)
            if output and output.produced_artifact and output.produced_artifact.artifact_type == required_artifact:
                return output.produced_artifact

        raise ValueError(f"Artifact {required_artifact} required for {project.name} not found")

    def _execute_stage(self, stage: Stage, project: Project, dry_run: bool = False) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage '{stage.value}' not defined on project '{project.name}'")

        executor = self._find_executor(stage, stage_name)
        if executor:
            try:
                self._logger.info(f'Executing {stage} for {project.name}')
                artifact: Optional[Artifact] = self._find_required_artifact(project, executor.required_artifact)
                result = Output(success=True, message='')
                if executor.before:
                    result = self._execute(executor.before, project, self._properties,
                                           self._find_required_artifact(project, executor.before.required_artifact),
                                           dry_run)
                if result.success:
                    result = self._execute(executor, project, self._properties, artifact, dry_run)
                    result.write(project.target_path, stage)
                if executor.after:
                    main_step_artifact = result.produced_artifact
                    result = self._execute(executor.after, project, self._properties, result.produced_artifact, dry_run)
                    if result.produced_artifact and result.produced_artifact.artifact_type != ArtifactType.NONE:
                        result.write(project.target_path, stage)
                    else:
                        result.produced_artifact = main_step_artifact

                return result
            except Exception as exc:
                self._logger.warning(
                    f"Execution of '{executor.meta.name}' for project '{project.name}' in stage {stage} "
                    f"failed with exception: {str(exc)}", exc_info=True)
                raise ValueError from exc
        else:
            self._logger.warning(f"No executor found for {stage_name} in stage {stage}")

        return Output(success=False, message=f"Executor '{stage_name}' for '{stage.value}' not known or registered")

    def execute(self, stage: Stage, project: Project, dry_run: bool = False) -> StepResult:
        step_output = self._execute_stage(stage, project, dry_run)
        return StepResult(stage=stage, project=project, output=step_output)
