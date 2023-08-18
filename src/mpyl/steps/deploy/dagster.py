"""
Step to deploy a dagster user code repository to k8s
"""
from functools import reduce
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
from .k8s.resources.dagster import to_user_code_values, to_grpc_server_entry, Constants
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

    @staticmethod
    def __flatten_result_messages(results: List[Output]) -> Output:
        def merge_outputs(acc: Output, curr: Output) -> Output:
            return Output(
                success=acc.success and curr.success,
                message=acc.message + "\n" + curr.message,
            )

        return (
            reduce(merge_outputs, results[1:], results[0])
            if len(results) > 1
            else results[0]
        )

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        context = cluster_config(
            step_input.run_properties.target, step_input.run_properties
        ).context

        version = get_version_of_deployment(
            context=context,
            namespace=Constants.DAGSTER_NAMESPACE,
            deployment=Constants.DAGSTER_DAGIT,
            version_label="app.kubernetes.io/version",
        )
        self._logger.info(f"Dagster Version: {version}")

        helm.add_repo(
            self._logger, Constants.DAGSTER_NAMESPACE, Constants.HELM_CHART_REPO
        )
        helm.update_repo(self._logger)

        name_suffix = (
            f"-{step_input.run_properties.versioning.identifier}"
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

        dagster_deploy_results = []
        helm_install_result = helm.install_with_values_yaml(
            logger=self._logger,
            step_input=step_input,
            values=user_code_deployment,
            release_name=convert_name_to_helm_release_name(
                step_input.project.name, name_suffix
            ),
            chart_name=Constants.CHART_NAME,
            namespace=Constants.DAGSTER_NAMESPACE,
            kube_context=context,
        )

        if helm_install_result.success and not step_input.dry_run:
            dagster_deploy_results.append(helm_install_result)

            config_map = get_config_map(
                context,
                Constants.DAGSTER_NAMESPACE,
                Constants.DAGSTER_WORKSPACE_CONFIGMAP,
            )
            dagster_workspace = yaml.safe_load(
                config_map.data[Constants.DAGSTER_WORKSPACE_FILE]
            )

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
                    field=Constants.DAGSTER_WORKSPACE_FILE,
                    data=dagster_workspace,
                )
                configmap_update_result = replace_config_map(
                    self._logger,
                    context,
                    Constants.DAGSTER_NAMESPACE,
                    Constants.DAGSTER_WORKSPACE_CONFIGMAP,
                    updated_config_map,
                )
                if configmap_update_result.success:
                    self._logger.info(
                        f"Successfully added {user_code_name_to_deploy} to dagster's workspace.yaml"
                    )
                    dagster_deploy_results.append(configmap_update_result)
                if not configmap_update_result.success:
                    return configmap_update_result

            # restarting ui and daemon
            rollout_restart_output = rollout_restart_deployment(
                self._logger, Constants.DAGSTER_NAMESPACE, Constants.DAGSTER_DAEMON
            )
            if rollout_restart_output.success:
                self._logger.info(rollout_restart_output.message)
                dagster_deploy_results.append(rollout_restart_output)
                rollout_restart_output = rollout_restart_deployment(
                    self._logger, Constants.DAGSTER_NAMESPACE, Constants.DAGSTER_DAGIT
                )
                if not rollout_restart_output.success:
                    return rollout_restart_output

                self._logger.info(rollout_restart_output.message)
                dagster_deploy_results.append(rollout_restart_output)
            else:
                return rollout_restart_output
        return self.__flatten_result_messages(dagster_deploy_results)
