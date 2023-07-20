"""
Step to deploy a dagster user code repository to k8s
"""
from logging import Logger

from .k8s import (
    helm,
    get_config_map_as_yaml,
    rollout_restart_deployment,
    cluster_config,
    replace_config_map,
)
from .k8s.resources.dagster import to_user_code_values, to_grpc_server_entry
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage, Target, get_env_variables


class DeployDagster(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Dagster Deploy",
                description="Deploy a dagster user code repository to k8s",
                version="0.0.1",
                stage=Stage.DEPLOY,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        namespace = "dagster"
        context = cluster_config(
            step_input.run_properties.target, step_input.run_properties
        ).context

        # get dagster version command
        version = "1.3.10"
        self._logger.info(f"Dagster Version: {version}")
        # checking dagster-dagit version
        helm.add_repo(self._logger, namespace, "https://dagster-io.github.io/helm")
        project = step_input.project
        name_suffix = (
            f"-pr-{step_input.run_properties.versioning.pr_number}"
            if step_input.run_properties.target == Target.PULL_REQUEST
            else ""
        )

        user_code_deployment = to_user_code_values(
            env_vars=get_env_variables(project, step_input.run_properties.target),
            env_secrets={},
            project_name=project.name,
            suffix=name_suffix,
            tag=step_input.run_properties.versioning.tag,
            repo_file_path=project.dagster.repo,
        )
        deploy_result = helm.install_with_values_yaml(
            logger=self._logger,
            step_input=step_input,
            values=user_code_deployment,
            release_name="uc",
            chart_name="dagster/dagster-user-deployments",
            namespace="dagster",
            kube_context=context,
        )

        # DagsterDeploy we "Apply it and retrieve it again to make sure it has the last-applied-configuration annotation"
        dagster_workspace = get_config_map_as_yaml(
            context, namespace, "dagster-workspace-yaml"
        )
        self._logger.info(f"Got type: {type(dagster_workspace)}")
        server_names = [
            w["grpc_server"] for w in dagster_workspace["workspace.yaml"]["load_from"]
        ]
        is_new_grpc_server = user_code_deployment["name"] not in server_names

        if is_new_grpc_server:
            self._logger.info("Adding new server")
            new_workspace_servers_list = dagster_workspace["workspace.yaml"][
                "load_from"
            ]
            new_workspace_servers_list.append(
                to_grpc_server_entry(
                    host=user_code_deployment["name"],
                    port=user_code_deployment["port"],
                    name=user_code_deployment["name"],
                )
            )
            dagster_workspace["workspace.yaml"][
                "load_from"
            ] = new_workspace_servers_list

            self._logger.info(dagster_workspace)

            replace_config_map(
                context, "dagster", "dagster-workspace-yaml", dagster_workspace
            )
        else:
            self._logger.info("Starting rollout restart of dagster-dagit...")
            rollout_restart_deployment(self._logger, namespace, "dagster-dagit")
            self._logger.info("Starting rollout restart of dagster-daemon...")
            rollout_restart_deployment(self._logger, namespace, "dagster-daemon")

        return deploy_result
