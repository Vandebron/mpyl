from logging import Logger
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from .build.echo import BuildEcho
from .build.dockerbuild import BuildDocker
from .deploy.echo import DeployEcho
from .models import Output, Input, BuildProperties, ArtifactType, Artifact
from .step import Step
from ..project import Project
from ..stage import Stage

yaml = YAML()


class Steps:
    _step_executors: set[Step]
    _logger: Logger

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._step_executors = {BuildEcho(logger), DeployEcho(logger), BuildDocker(logger)}
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

        path = Path(f'{project.target_path}/BUILD.yml')
        required_artifact = step.required_artifact
        if step.required_artifact and required_artifact != ArtifactType.NONE and path.exists():
            with open(path) as f:
                output: Output = yaml.load(f)
                artifact = output.produced_artifact
                if artifact is None or artifact.artifact_type != required_artifact:
                    raise ValueError(
                        f"Artifact {required_artifact} required for {project.name}, found: {artifact}")
                return artifact
        return None

    def execute(self, stage: Stage, project: Project, properties: BuildProperties) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage ${stage.value} not defined on project ${project.name}")

        executor = self._find_executor(stage, stage_name)
        if executor:
            try:
                artifact: Optional[Artifact] = self._find_required_artifact(project, executor)

                path = Path(project.target_path)
                path.mkdir(parents=True, exist_ok=True)
                with Path(path, f"{stage.name}.yml").open(mode='w+') as file:
                    result: Output = self._execute(executor, project, properties, artifact)
                    yaml.dump(result, file)
                    return result
            except Exception as e:
                self._logger.warning(
                    f"Execution of '{executor.meta.name}' for project '{project.name}' in stage {stage} "
                    f"failed with  exception: '{e}' ")

        return Output(success=False, message=f"Executor {stage.value} not defined on project {project.name}")
