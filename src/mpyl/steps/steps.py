""" Entry point of MPyL. Loads all available Step implementations and triggers their execution based on the specified
Project and Stage.
"""
import itertools
import pkgutil
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Optional
from unittest import TestSuite

from ruamel.yaml import YAML  # type: ignore

from . import Step
from .build.dockerbuild import BuildDocker
from .build.echo import BuildEcho
from .build.sbt import BuildSbt
from .deploy.echo import DeployEcho
from .deploy.ephemeral_docker_deploy import EphemeralDockerDeploy
from .deploy.kubernetes import DeployKubernetes
from .deploy.kubernetes_job import DeployKubernetesJob
from .deploy.kubernetes_spark_job import DeployKubernetesSparkJob
from .models import Output, Input, RunProperties, ArtifactType, Artifact
from .test.dockertest import TestDocker
from .test.echo import TestEcho
from .test.sbt import TestSbt
from ..project import Project
from ..project import Stage
from ..utilities.junit import to_test_suites
from ..validation import validate

yaml = YAML()


class ExecutionException(Exception):
    """ Exception thrown when a step execution fails. """

    def __init__(self, project_name: str, executor: str, stage: str, message: str):
        self.project_name = project_name
        self.executor = executor
        self.stage = stage
        self.message = message
        super().__init__(self.message)


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

        self._step_executors: dict[Stage, set[Step]] = {
            Stage.BUILD: {
                BuildEcho(logger),
                BuildSbt(logger),
                BuildDocker(logger)
            },
            Stage.TEST: {
                TestEcho(logger),
                TestSbt(logger),
                TestDocker(logger)
            },
            Stage.DEPLOY: {
                DeployEcho(logger),
                DeployKubernetes(logger),
                DeployKubernetesJob(logger),
                DeployKubernetesSparkJob(logger),
                EphemeralDockerDeploy(logger)
            },
            Stage.POST_DEPLOY: set(),
        }

        self._properties = properties
        for stage, steps in self._step_executors.items():
            self._logger.debug(f"Registered executors for stage {stage.name}: "  # pylint: disable=E1101
                               f"{[step.meta.name for step in steps]}")

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

    def _execute_after_(self, main_result: Output, step: Step, project: Project, stage: Stage,
                        dry_run: bool = False) -> Output:
        main_step_artifact = main_result.produced_artifact
        after_result = self._execute(step, project, self._properties, main_step_artifact, dry_run)
        if after_result.produced_artifact and after_result.produced_artifact.artifact_type != ArtifactType.NONE:
            after_result.write(project.target_path, stage)
        else:
            after_result.produced_artifact = main_step_artifact

        if not main_result.success:
            after_result.success = False

        return after_result

    def _validate_project_against_config(self, project: Project) -> Optional[Output]:
        allowed_maintainers = set(self._properties.config.get('project', {}).get('allowedMaintainers', []))
        not_allowed = set(project.maintainer).difference(allowed_maintainers)
        if not_allowed:
            return Output(success=False, message=f"Maintainer(s) '{', '.join(not_allowed)}' not defined in config")
        return None

    def _execute_stage(self, stage: Stage, project: Project, dry_run: bool = False) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage '{stage.value}' not defined on project '{project.name}'")

        invalid_maintainers = self._validate_project_against_config(project)
        if invalid_maintainers:
            return invalid_maintainers

        executor: Optional[Step] = self._find_executor(stage, stage_name)
        if executor:
            try:
                self._logger.info(f'Executing {stage} for {project.name}')
                artifact: Optional[Artifact] = self._find_required_artifact(project, executor.required_artifact)
                if executor.before:
                    before_result = self._execute(executor.before, project, self._properties,
                                                  self._find_required_artifact(project,
                                                                               executor.before.required_artifact),
                                                  dry_run)
                    if not before_result.success:
                        return before_result

                result = self._execute(executor, project, self._properties, artifact, dry_run)
                result.write(project.target_path, stage)

                if executor.after:
                    return self._execute_after_(result, executor.after, project, stage, dry_run)

                return result
            except Exception as exc:
                message = str(exc)
                self._logger.warning(
                    f"Execution of '{executor.meta.name}' for project '{project.name}' in stage {stage} "
                    f"failed with exception: {message}", exc_info=True)
                raise ExecutionException(project.name, executor.meta.name, stage.name, message) from exc
        else:
            self._logger.warning(f"No executor found for {stage_name} in stage {stage}")

        return Output(success=False, message=f"Executor '{stage_name}' for '{stage.value}' not known or registered")

    def execute(self, stage: Stage, project: Project, dry_run: bool = False) -> StepResult:
        """
        :param stage: the stage to execute
        :param project: the project metadata
        :param dry_run: indicates whether artifacts should be submitted or deployed for real
        :return: StepResult
        :raise ExecutionException
        """
        step_output = self._execute_stage(stage, project, dry_run)
        return StepResult(stage=stage, project=project, output=step_output)
