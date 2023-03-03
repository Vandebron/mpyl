""" Entry point of MPyL. Loads all available Step implementations and triggers their execution based on the specified
Project and Stage.
"""

import pkgutil
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Optional

from ruamel.yaml import YAML  # type: ignore

from . import Step
from .build.dockerbuild import BuildDocker
from .build.echo import BuildEcho
from .build.sbt import BuildSbt
from .deploy.echo import DeployEcho
from .deploy.kubernetes import DeployKubernetes
from .models import Output, Input, RunProperties, ArtifactType, Artifact
from .test.dockertest import TestDocker
from .test.echo import TestEcho
from .test.sbt import TestSbt
from ..project import Project
from ..project import Stage
from ..validation import validate

yaml = YAML()


@dataclass(frozen=True)
class StepResult:
    stage: Stage
    project: Project
    output: Output
    timestamp: datetime = datetime.now()


class Steps:
    """ Executor of individual steps within a pipeline. """
    _step_executors: dict[Stage, set[Step]]
    _logger: Logger
    _properties: RunProperties

    def __init__(self, logger: Logger, properties: RunProperties) -> None:
        schema_dict = pkgutil.get_data(__name__, "../schema/mpyl_config.schema.yml")

        if schema_dict:
            schema = yaml.load(schema_dict.decode('utf-8'))
            validate(properties.config, schema)

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
                DeployKubernetes(logger)
            }
        }

        self._properties = properties
        for stage, steps in self._step_executors.items():
            self._logger.info(f"Registered executors for stage {stage.name}: "
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
    def _find_required_artifact(project: Project, step: Step) -> Optional[Artifact]:
        if step.required_artifact is None:
            return None

        required_artifact = step.required_artifact
        if step.required_artifact and required_artifact != ArtifactType.NONE:
            output: Optional[Output] = Output.try_read(project.target_path, Stage.BUILD)
            if output is None or output.produced_artifact \
                    and output.produced_artifact.artifact_type != required_artifact:
                raise ValueError(
                    f"Artifact {required_artifact} required for {project.name}, found: {output}")

            return output.produced_artifact
        return None

    def _execute_stage(self, stage: Stage, project: Project, dry_run: bool = False) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage '{stage.value}' not defined on project '{project.name}'")

        executor = self._find_executor(stage, stage_name)
        if executor:
            try:
                artifact: Optional[Artifact] = self._find_required_artifact(project, executor)

                result = self._execute(executor, project, self._properties, artifact, dry_run)
                if executor.after:
                    executor = executor.after
                    result = self._execute(executor, project, self._properties, result.produced_artifact, dry_run)
                result.write(project.target_path, stage)
                return result
            except Exception as exc:
                self._logger.warning(
                    f"Execution of '{executor.meta.name}' for project '{project.name}' in stage {stage} "
                    f"failed with exception: {str(exc)}", exc_info=True)
                raise ValueError from exc
        else:
            self._logger.warning(f"No executor found for {stage_name} in stage {stage}")

        return Output(success=False, message=f"Executor {stage.value} not defined on project {project.name}")

    def execute(self, stage: Stage, project: Project, dry_run: bool = False) -> StepResult:
        step_output = self._execute_stage(stage, project, dry_run)
        return StepResult(stage=stage, project=project, output=step_output)
