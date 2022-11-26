from logging import Logger
from typing import Optional

from .build.echo import BuildEcho
from .build.dockerbuild import BuildDocker
from .deploy.echo import DeployEcho
from .deploy.kubernetes import DeployKubernetes
from .models import Output, Input, BuildProperties
from .step import Step
from ..project import Project
from ..stage import Stage


class Steps:
    _step_executors: set[Step]
    _logger: Logger

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._step_executors = {BuildEcho(logger), DeployEcho(logger), BuildDocker(logger), DeployKubernetes(logger)}
        for step in self._step_executors:
            self._logger.debug(f"Registered executor ${step.meta.name}")

    def _find_executor(self, stage: Stage, step_name: str) -> Optional[Step]:
        executors = filter(lambda e: e.meta.stage == stage and step_name == e.meta.name, self._step_executors)
        return next(executors, None)

    def execute(self, stage: Stage, project: Project, properties: BuildProperties) -> Output:
        stage_name = project.stages.for_stage(stage)
        if stage_name is None:
            return Output(success=False, message=f"Stage ${stage.value} not defined on project ${project.name}")

        executor = self._find_executor(stage, stage_name)
        if executor:
            result = executor.execute(Input(project, properties))
            if result.success:
                self._logger.info(
                    f"Execution of {executor.meta.name} succeeded for {project.name} with outcome {result.message}")
            else:
                self._logger.warning(
                    f"Execution of {executor.meta.name} failed for {project.name} with outcome {result.message}")
            return result

        return Output(success=False, message=f"Executor {stage.value} not defined on project {project.name}")
