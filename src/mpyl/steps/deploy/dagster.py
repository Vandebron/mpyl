"""
Step to deploy a dagster user code repository to k8s
"""
from logging import Logger
from typing import List

import yaml

from .k8s import (
    helm,
    get_config_map,
    rollout_restart_deployment,
    cluster_config,
    replace_config_map,
    update_config_map_field,
    get_version_of_deployment,
)
from .k8s.resources.dagster import to_user_code_values, to_grpc_server_entry
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage, Target
from ...utilities.docker import DockerConfig
from ...utilities.helm import convert_name_to_helm_release_name


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

        version = get_version_of_deployment(
            context=context,
            namespace=namespace,
            deployment="dagster-dagit",
            version_label="app.kubernetes.io/version",
        )
        self._logger.info(f"Dagster Version: {version}")

        helm.add_repo(self._logger, namespace, "https://dagster-io.github.io/helm")

        name_suffix = (
            f"-pr-{step_input.run_properties.versioning.pr_number}"
            if step_input.run_properties.target == Target.PULL_REQUEST
            else ""
        )

        user_code_deployment = to_user_code_values(
            project=step_input.project,
            name_suffix=name_suffix,
            run_properties=step_input.run_properties,
            docker_config=DockerConfig.from_dict(step_input.run_properties.config),
        )
        user_code_name_to_deploy = user_code_deployment["deployments"][0]["name"]

        self._logger.debug(f"Deploying user code with values: {user_code_deployment}")

        deploy_result = helm.install_with_values_yaml(
            logger=self._logger,
            step_input=step_input,
            values=user_code_deployment,
            release_name=convert_name_to_helm_release_name(
                step_input.project.name, name_suffix
            ),
            chart_name="dagster/dagster-user-deployments",
            namespace=namespace,
            kube_context=context,
        )

        if deploy_result.success and not step_input.dry_run:
            config_map = get_config_map(context, namespace, "dagster-workspace-yaml")
            dagster_workspace = yaml.safe_load(config_map.data["workspace.yaml"])

            server_names = [
                w["grpc_server"]["location_name"]
                for w in dagster_workspace["load_from"]
            ]

            # If the server new (not in existing workspace.yml), we append it
            if user_code_name_to_deploy not in server_names:
                self._logger.info(
                    f"Adding new server {user_code_name_to_deploy} to dagster's workspace.yaml"
                )
                dagster_workspace["load_from"].append(
                    to_grpc_server_entry(
                        host=user_code_deployment["deployments"][0]["name"],
                        port=user_code_deployment["deployments"][0]["port"],
                        location_name=user_code_deployment["deployments"][0]["name"],
                    )
                )
                updated_config_map = update_config_map_field(
                    config_map=config_map,
                    field="workspace.yaml",
                    data=dagster_workspace,
                )
                replaced_configmap_result = replace_config_map(
                    self._logger,
                    context,
                    "dagster",
                    "dagster-workspace-yaml",
                    updated_config_map,
                )
                if not replaced_configmap_result.success:
                    return replaced_configmap_result
            else:
                rollout_restart_ouput = rollout_restart_deployment(
                    self._logger, namespace, "dagster-dagit"
                )
                if rollout_restart_ouput.success:
                    rollout_restart_ouput = rollout_restart_deployment(
                        self._logger, namespace, "dagster-dagit"
                    )
                    if not rollout_restart_ouput.success:
                        return rollout_restart_ouput
                else:
                    return rollout_restart_ouput
        return deploy_result
