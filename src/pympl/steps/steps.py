from logging import Logger
from typing import Optional

from ruamel.yaml import YAML  # type: ignore

from .build.dockerbuild import BuildDocker
from .build.echo import BuildEcho
from .deploy.echo import DeployEcho
from .models import Output, Input, BuildProperties, ArtifactType, Artifact
from .step import Step
from .test.sbt import SbtTest
from ..project import Project
from ..stage import Stage

yaml = YAML()


class Steps:
    _step_executors: set[Step]
    _logger: Logger

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._step_executors = {BuildEcho(logger), DeployEcho(logger), BuildDocker(logger), SbtTest(logger)}
        for step in self._step_executors:
            self._logger.debug(f"Registered executor ${step.meta.name}")

    def _find_executor(self, stage: Stage, step_name: str) -> Optional[Step]:
        executors = filter(lambda e: e.meta.stage == stage and step_name == e.meta.name, self._step_executors)
        return next(executors, None)

    def _execute(self, executor: Step, project: Project, properties: BuildProperties,
                 artifact: Optional[Artifact]) -> Output:
        result = executor.execute(Input(project, properties, required_artifact=artifact))
        if result.success:
            self._logger.info(
                f"Execution of {executor.meta.name} succeeded for '{project.name}' with outcome {result.message}")
        else:
            self._logger.warning(
                f"Execution of {executor.meta.name} failed for '{project.name}' with outcome {result.message}")
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

    def execute(self, stage: Stage, project: Project, properties: BuildProperties) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage ${stage.value} not defined on project ${project.name}")

        executor = self._find_executor(stage, stage_name)
        if executor:
            try:
                artifact: Optional[Artifact] = self._find_required_artifact(project, executor)

                result = self._execute(executor, project, properties, artifact)
                result.write(project.target_path, stage)
                return result
            except Exception as e:
                self._logger.warning(
                    f"Execution of '{executor.meta.name}' for project '{project.name}' in stage {stage} "
                    f"failed with  exception: '{e}' ")

        return Output(success=False, message=f"Executor {stage.value} not defined on project {project.name}")
