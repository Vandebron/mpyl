""" Step that runs relevant cypress tests in the post deploy stage """
import itertools
import os
from concurrent.futures import ProcessPoolExecutor, Future
from logging import Logger

from kubernetes.config.kube_config import KubeConfigMerger
from python_on_whales import docker, Container, DockerException

from . import STAGE_NAME
from .. import Step, Meta
from ..models import ArtifactType, Input, Output, input_to_artifact
from ...project import Target
from ...utilities.cypress import CypressConfig
from ...utilities.docker import execute_with_stream
from ...utilities.junit import JunitTestSpec


class CypressTest(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Cypress Test",
                description="Step to run cypress tests",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.JUNIT_TESTS,
            required_artifact=ArtifactType.NONE,
        )

    def execute(self, step_input: Input) -> Output:  # pylint: disable=too-many-locals
        if step_input.run_properties.target == Target.PRODUCTION:
            return Output(
                success=True, message="Cypress tests are not run on production"
            )

        self._logger.info(
            f"Running cypress tests for project {step_input.project.name}"
        )
        cypress_config = CypressConfig.from_config(step_input.run_properties.config)
        volume_path = os.path.join(os.getcwd(), cypress_config.cypress_source_code_path)

        if (
            step_input.project.dependencies
            and step_input.project.dependencies.postdeploy
        ):
            specs_string = ",".join(step_input.project.dependencies.postdeploy)
        else:
            raise ValueError("No cypress specs are defined in the project dependencies")

        docker_container = self._get_docker_container(volume_path, cypress_config)
        reports_folder = f"reports/{step_input.project.name}"
        artifact = input_to_artifact(
            artifact_type=ArtifactType.JUNIT_TESTS,
            step_input=step_input,
            spec=JunitTestSpec(test_output_path=f"{volume_path}/{reports_folder}"),
        )
        try:
            self._run_container_preparation_steps(
                docker_container, step_input, reports_folder
            )
            record_key = cypress_config.record_key
            run_command = ""

            if record_key:
                ci_build_id = f"{cypress_config.ci_build_id}-{step_input.project.name}"
                machines = [1, 2, 3, 4]
                threads: list[Future] = []

                for machine in machines:
                    run_command = (
                        f'bash -c "Xvfb :10{machine} & XDG_CONFIG_HOME=/tmp/cyhome{machine} '
                        f"DISPLAY=:10{machine}  yarn cypress run --spec '{specs_string}' --ci-build-id "
                        f"{ci_build_id} --parallel --reporter-options "
                        f'"mochaFile={reports_folder}/[hash].xml" --record --key '
                        'b6a2aab1-0b80-4ca0-a56c-1c8d98a8189c || true "'
                    )
                    executor = ProcessPoolExecutor(max_workers=len(machines))
                    threads.append(
                        executor.submit(
                            execute_with_stream,
                            logger=self._logger,
                            container=docker_container,
                            command=run_command,
                            task_name="Running cypress tests parallel",
                            multiprocess=True,
                        )
                    )

                result: list[str] = list(
                    itertools.chain.from_iterable(
                        [thread.result() for thread in threads]
                    )
                )
            else:
                run_command = (
                    f'bash -c "yarn cypress run --spec "{specs_string}" --reporter-options '
                    f'mochaFile="{reports_folder}/[hash].xml" || true"'
                )
                result = execute_with_stream(
                    logger=self._logger,
                    container=docker_container,
                    command=run_command,
                    task_name="Running cypress tests",
                )

            for stdout in result:
                if record_key and "Recorded Run" in stdout:
                    artifact = input_to_artifact(
                        artifact_type=ArtifactType.JUNIT_TESTS,
                        step_input=step_input,
                        spec=JunitTestSpec(
                            test_output_path=f"{volume_path}/{reports_folder}",
                            test_results_url=stdout.rstrip().rsplit(
                                "Recorded Run: ", 1
                            )[1],
                        ),
                    )
                if "error Command failed with exit code" in stdout:
                    raise DockerException(command_launched=[run_command], return_code=1)
        except DockerException:
            return Output(
                success=False,
                message=f"Cypress tests for project {step_input.project.name} have one or more failures",
                produced_artifact=artifact,
            )
        finally:
            docker_container.stop()
            docker_container.remove()

        return Output(
            success=True,
            message=f"Cypress tests for project {step_input.project.name} passed",
            produced_artifact=artifact,
        )

    def _get_docker_container(
        self, volume_path: str, cypress_config: CypressConfig
    ) -> Container:
        custom_image_tag = "mpyl/cypress"
        docker.build(
            context_path=volume_path,
            tags=[custom_image_tag],
            file=f"{volume_path}/Dockerfile-mpyl",
        )

        config_merger = KubeConfigMerger(paths=cypress_config.kubectl_config_path)
        config_paths = []
        for path in config_merger.paths:
            config_paths.append((path, f"/root/.kube/{path.split('/')[-1]}"))

        docker_container = docker.run(
            image=custom_image_tag,
            interactive=True,
            detach=True,
            volumes=[
                (volume_path, "/cypress"),
            ]
            + config_paths,
            envs={"KUBECONFIG": ":".join(map(lambda p: p[1], config_paths))},
            workdir="/cypress",
        )
        if not isinstance(docker_container, Container):
            raise TypeError("Docker run command should return a container")

        return docker_container

    def _run_container_preparation_steps(
        self, docker_container: Container, step_input: Input, reports_folder: str
    ) -> None:
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command=f"rm -rf {reports_folder} dist",
            task_name="Remove old files",
        )
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command='bash -c "cp cypress.env.json.example cypress.env.json && '
            f"sed -i 's/acceptance/"
            f"{CypressTest._target_to_test_target(step_input.run_properties.target)}"
            f"/' cypress.env.json && "
            f"sed -i 's/{{PR_NUMBER}}/{step_input.run_properties.versioning.pr_number}/' "
            'cypress.env.json"',
            task_name="Preparing env file",
        )
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command="yarn install",
            task_name="Running yarn install",
        )
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command="yarn cypress install",
            task_name="Installing cypress",
        )
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command="yarn cypress verify",
            task_name="Verifying cypress",
        )
        execute_with_stream(
            logger=self._logger,
            container=docker_container,
            command="yarn tsc",
            task_name="Compiling typescript",
        )

    @staticmethod
    def _target_to_test_target(target: Target) -> str:
        if target == Target.PULL_REQUEST_BASE:
            return "test"
        if target == Target.ACCEPTANCE:
            return "acceptance"

        return "pr"
