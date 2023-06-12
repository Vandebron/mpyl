from logging import Logger
from typing import Optional

from . import Step
from .build.dockerbuild import BuildDocker
from .build.echo import BuildEcho
from .build.sbt import BuildSbt
from .deploy.echo import DeployEcho
from .deploy.ephemeral_docker_deploy import EphemeralDockerDeploy
from .deploy.kubernetes import DeployKubernetes
from .deploy.kubernetes_job import DeployKubernetesJob
from .deploy.kubernetes_spark_job import DeployKubernetesSparkJob
from .postdeploy.cypress_test import CypressTest
from .test.dockertest import TestDocker
from .test.echo import TestEcho
from .test.sbt import TestSbt


class StepsCollection:
    _step_executors: set[Step]

    def __init__(self, logger: Logger) -> None:
        self._step_executors = {
            BuildEcho(logger),
            BuildSbt(logger),
            BuildDocker(logger),
            TestEcho(logger),
            TestSbt(logger),
            TestDocker(logger),
            DeployEcho(logger),
            DeployKubernetes(logger),
            DeployKubernetesJob(logger),
            DeployKubernetesSparkJob(logger),
            EphemeralDockerDeploy(logger),
            CypressTest(logger)
        }

    def add_executor(self, step: Step):
        self._step_executors.add(step)

    def get_executor(self, stage: str, step_name: str) -> Optional[Step]:
        executors = filter(lambda e: step_name == e.meta.name and e.meta.stage == stage, self._step_executors)
        return next(executors, None)
