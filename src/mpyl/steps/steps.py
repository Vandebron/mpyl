""" Entry point of MPyL. Loads all available Step implementations and triggers their execution based on the specified
Project and Stage.
"""
import pkgutil
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML  # type: ignore

from . import Step
from .collection import StepsCollection
from .models import Output, Input, RunProperties, ArtifactType, Artifact
from ..project import Project
from ..project import Stage
from ..project_execution import ProjectExecution
from ..validation import validate

yaml = YAML()


class ExecutionException(Exception):
    """Exception thrown when a step execution fails."""

    def __init__(self, project_name: str, executor: str, stage: str, message: str):
        self.project_name = project_name
        self.executor = executor
        self.stage = stage
        self.message = message
        super().__init__(self.message)

    def __reduce__(self):
        return ExecutionException, (
            self.project_name,
            self.executor,
            self.stage,
            self.message,
        )


@dataclass(frozen=True)
class StepResult:
    stage: Stage
    project: Project
    output: Output
    timestamp: datetime = datetime.now()


class Steps:
    """Executor of individual steps within a pipeline."""

    _logger: Logger
    _properties: RunProperties
    _steps_collection: StepsCollection

    def __init__(
        self,
        logger: Logger,
        properties: RunProperties,
        steps_collection: Optional[StepsCollection] = None,
        root_dir: Path = Path("."),
    ) -> None:
        self._logger = logger
        self._properties = properties
        self._steps_collection = steps_collection or StepsCollection(logger)

        schema_dict = pkgutil.get_data(__name__, "../schema/mpyl_config.schema.yml")

        if schema_dict:
            validate(properties.config, schema_dict.decode("utf-8"), root_dir=root_dir)

    def _execute(
        self,
        executor: Step,
        project_execution: ProjectExecution,
        properties: RunProperties,
        artifact: Optional[Artifact],
        dry_run: bool = False,
    ) -> Output:
        self._logger.info(
            f"Executing {executor.meta.name} for '{project_execution.name}'"
        )
        required = executor.required_artifact
        if (
            artifact is not None
            and required.value != ArtifactType.NONE.value  # pylint: disable=no-member
            and required.value  # pylint: disable=no-member
            != artifact.artifact_type.value  # pylint: disable=no-member
        ):
            return Output(
                success=False,
                message=f"Required artifact of type {required.name} for {executor.meta.name} "
                f"on {project_execution.name} does not match {artifact.artifact_type.name}.",
            )

        result = executor.execute(
            Input(
                project_execution=project_execution,
                run_properties=properties,
                required_artifact=artifact,
                dry_run=dry_run,
            )
        )
        if result.success:
            self._logger.info(
                f"Execution of {executor.meta.name} succeeded for '{project_execution.name}' with outcome '{result.message}'"  # pylint: disable=line-too-long
            )
        else:
            self._logger.warning(
                f"Execution of {executor.meta.name} failed for '{project_execution.name}' with outcome '{result.message}'"  # pylint: disable=line-too-long
            )
        return result

    @staticmethod
    def _find_required_artifact(
        project: Project, stages: list[Stage], required_artifact: Optional[ArtifactType]
    ) -> Optional[Artifact]:
        if not required_artifact or required_artifact == ArtifactType.NONE:
            return None

        for stage in stages:
            output: Optional[Output] = Output.try_read(project.target_path, stage.name)
            if (
                output
                and output.produced_artifact
                and output.produced_artifact.artifact_type == required_artifact
            ):
                return output.produced_artifact

        raise ValueError(
            f"Artifact {required_artifact} required for {project.name} not found"
        )

    def _execute_after_(
        self,
        main_result: Output,
        step: Step,
        project_execution: ProjectExecution,
        stage: Stage,
        dry_run: bool = False,
    ) -> Output:
        main_step_artifact = main_result.produced_artifact
        after_result = self._execute(
            executor=step,
            project_execution=project_execution,
            properties=self._properties,
            artifact=main_step_artifact,
            dry_run=dry_run,
        )
        if (
            after_result.produced_artifact
            and after_result.produced_artifact.artifact_type != ArtifactType.NONE
        ):
            after_result.write(project_execution.project.target_path, stage.name)
        else:
            after_result.produced_artifact = main_step_artifact

        if not main_result.success:
            after_result.message = main_result.message
            after_result.success = False

        return after_result

    def _validate_project_against_config(self, project: Project) -> Optional[Output]:
        allowed_maintainers = set(
            self._properties.config.get("project", {}).get("allowedMaintainers", [])
        )
        not_allowed = set(project.maintainer).difference(allowed_maintainers)
        if not_allowed:
            return Output(
                success=False,
                message=f"Maintainer(s) '{', '.join(not_allowed)}' not defined in config",
            )
        return None

    def _execute_stage(
        self,
        stage: Stage,
        project_execution: ProjectExecution,
        dry_run: bool = False,
    ) -> Output:
        step_name = project_execution.project.stages.for_stage(stage.name)
        if step_name is None:
            return Output(
                success=False,
                message=f"Stage '{stage.name}' not defined on project '{project_execution.name}'",
            )

        invalid_maintainers = self._validate_project_against_config(
            project_execution.project
        )
        if invalid_maintainers:
            return invalid_maintainers

        executor: Optional[Step] = self._steps_collection.get_executor(stage, step_name)
        if not executor:
            self._logger.error(
                f"No executor found for {step_name} in stage {stage.name}"
            )

            return Output(
                success=False,
                message=f"Executor '{step_name}' for '{stage.name}' not known or registered",
            )

        try:
            self._logger.info(
                f"Executing {stage.name} {stage.icon} for {project_execution.name}"
            )
            artifact: Optional[Artifact] = self._find_required_artifact(
                project_execution.project,
                self._properties.stages,
                executor.required_artifact,
            )
            if executor.before:
                before_result = self._execute(
                    executor=executor.before,
                    project_execution=project_execution,
                    properties=self._properties,
                    artifact=self._find_required_artifact(
                        project_execution.project,
                        self._properties.stages,
                        executor.before.required_artifact,
                    ),
                    dry_run=dry_run,
                )
                if not before_result.success:
                    return before_result

            result = self._execute(
                executor=executor,
                project_execution=project_execution,
                properties=self._properties,
                artifact=artifact,
                dry_run=dry_run,
            )
            result.write(project_execution.project.target_path, stage.name)

            if executor.after and result.success:
                return self._execute_after_(
                    result, executor.after, project_execution, stage, dry_run
                )

            return result
        except Exception as exc:
            message = str(exc)
            self._logger.warning(
                f"Execution of '{executor.meta.name}' for project '{project_execution.name}' in stage {stage.name} "
                f"failed with exception: {message}",
                exc_info=True,
            )
            raise ExecutionException(
                project_execution.name, executor.meta.name, stage.name, message
            ) from exc

    def execute(
        self,
        stage: str,
        project_execution: ProjectExecution,
        dry_run: bool = False,
    ) -> StepResult:
        """
        :param stage: the stage to execute
        :param project: the project metadata
        :param project_execution: the project execution information
        :param dry_run: indicates whether artifacts should be submitted or deployed for real
        :return: StepResult
        :raise ExecutionException
        """
        stage_object = self._properties.to_stage(stage)
        step_output = self._execute_stage(
            stage=stage_object,
            project_execution=project_execution,
            dry_run=dry_run,
        )
        return StepResult(
            stage=stage_object, project=project_execution.project, output=step_output
        )
