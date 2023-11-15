"""
Step to deploy a dagster user code repository to k8s
"""
from functools import reduce
from logging import Logger
from pathlib import Path
from typing import List

import yaml
from kubernetes import config, client

from . import STAGE_NAME
from .k8s import (
    helm,
    get_config_map,
    rollout_restart_deployment,
    cluster_config,
    replace_config_map,
    update_config_map_field,
    get_version_of_deployment,
)
from .k8s.helm import write_chart
from .k8s.resources.dagster import to_user_code_values, to_grpc_server_entry, Constants
from .. import Step, Meta, ArtifactType, Input, Output
from ...utilities.dagster import DagsterConfig
from ...utilities.docker import DockerConfig
from ...utilities.helm import convert_to_helm_release_name, get_name_suffix


class DeployDagster(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="Dagster Deploy",
                description="Deploy a dagster user code repository to k8s",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    def __evaluate_results(self, results: List[Output]):
        return (
            reduce(
                self.__flatten_result_messages,
                results[1:],
                results[0],
            )
            if len(results) > 1
            else results[0]
        )

    @staticmethod
    def __flatten_result_messages(acc: Output, curr: Output) -> Output:
        return Output(
            success=acc.success and curr.success,
            message=f"{acc.message}\n{curr.message}",
        )

    # pylint: disable=R0914
    def execute(self, step_input: Input) -> Output:
        """
        Deploys the docker image produced in the build stage as a Dagster user-code-deployment
        """
        properties = step_input.run_properties
        context = cluster_config(properties.target, properties).context
        dagster_config: DagsterConfig = DagsterConfig.from_dict(properties.config)
        dagster_deploy_results = []

        config.load_kube_config(context=context)
        core_api = client.CoreV1Api()
        apps_api = client.AppsV1Api()

        dagster_version = get_version_of_deployment(
            apps_api=apps_api,
            namespace=dagster_config.base_namespace,
            deployment=dagster_config.webserver,
            version_label="app.kubernetes.io/version",
        )
        self._logger.info(f"Dagster Version: {dagster_version}")

        result = helm.add_repo(
            self._logger, dagster_config.base_namespace, Constants.HELM_CHART_REPO
        )
        dagster_deploy_results.append(result)
        if not result.success:
            return self.__evaluate_results(dagster_deploy_results)

        result = helm.update_repo(self._logger)
        dagster_deploy_results.append(result)
        if not result.success:
            return self.__evaluate_results(dagster_deploy_results)

        name_suffix = get_name_suffix(properties)

        user_code_deployment = to_user_code_values(
            project=step_input.project,
            name_suffix=name_suffix,
            run_properties=properties,
            service_account_override=dagster_config.global_service_account_override,
            docker_config=DockerConfig.from_dict(properties.config),
        )

        self._logger.debug(f"Deploying user code with values: {user_code_deployment}")

        values_path = Path(step_input.project.target_path)
        self._logger.info(f"Writing Helm values to {values_path}")
        write_chart(
            chart={},
            chart_path=values_path,
            chart_metadata="",
            values=user_code_deployment,
        )

        helm_install_result = helm.install_chart_with_values(
            logger=self._logger,
            dry_run=step_input.dry_run,
            values_path=values_path / Path("values.yaml"),
            release_name=convert_to_helm_release_name(
                step_input.project.name, name_suffix
            ),
            chart_version=dagster_version,
            chart_name=Constants.CHART_NAME,
            namespace=dagster_config.base_namespace,
            kube_context=context,
        )

        dagster_deploy_results.append(helm_install_result)
        if helm_install_result.success and not step_input.dry_run:
            config_map = get_config_map(
                core_api,
                dagster_config.base_namespace,
                dagster_config.workspace_config_map,
            )
            dagster_workspace = yaml.safe_load(
                config_map.data[dagster_config.workspace_file_key]
            )

            server_names = [
                w["grpc_server"]["location_name"]
                for w in dagster_workspace["load_from"]
            ]

            # If the server new (not in existing workspace.yml), we append it
            user_code_name_to_deploy = user_code_deployment["deployments"][0]["name"]
            if user_code_name_to_deploy not in server_names:
                self._logger.info(
                    f"Adding new server {user_code_name_to_deploy} to dagster's workspace.yaml"
                )
                dagster_workspace["load_from"].append(
                    to_grpc_server_entry(
                        host=user_code_name_to_deploy,
                        port=user_code_deployment["deployments"][0]["port"],
                        location_name=user_code_name_to_deploy,
                    )
                )
                updated_config_map = update_config_map_field(
                    config_map=config_map,
                    field=dagster_config.workspace_file_key,
                    data=dagster_workspace,
                )
                config_map_update_result = replace_config_map(
                    core_api,
                    dagster_config.base_namespace,
                    dagster_config.workspace_config_map,
                    updated_config_map,
                )

                dagster_deploy_results.append(config_map_update_result)
                if config_map_update_result.success:
                    self._logger.info(
                        f"Successfully added {user_code_name_to_deploy} to dagster's workspace.yaml"
                    )

                    # restarting ui and daemon
                    rollout_restart_output = rollout_restart_deployment(
                        self._logger,
                        apps_api,
                        dagster_config.base_namespace,
                        dagster_config.daemon,
                    )

                    dagster_deploy_results.append(rollout_restart_output)
                    if rollout_restart_output.success:
                        self._logger.info(rollout_restart_output.message)
                        rollout_restart_output = rollout_restart_deployment(
                            self._logger,
                            apps_api,
                            dagster_config.base_namespace,
                            dagster_config.webserver,
                        )
                        dagster_deploy_results.append(rollout_restart_output)
                        self._logger.info(rollout_restart_output.message)
        return self.__evaluate_results(dagster_deploy_results)
