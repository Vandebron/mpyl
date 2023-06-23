from logging import Logger

from .k8s import deploy_helm_chart, helm, get_key_of_config_map, rollout_restart_deployment
from .k8s.chart import ChartBuilder, to_dagster_code_chart
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage
from ...stages.discovery import find_deploy_set
from ...utilities.repo import RepoConfig


class DeployDagster(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Job Deploy',
            description='Deploy a job to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        namespace = 'dagster'

        builder = ChartBuilder(step_input, find_deploy_set(RepoConfig.from_config(step_input.run_properties.config)))
        chart = to_dagster_code_chart(builder)

        # TODO get dagster version command
        self._logger.info(f'Dagster Version: 1.3.10')
        self._logger.info(f"Namespace will be overwritten and project will be pushed to {namespace}")
        # namespace: dagster
        # checking dagster-dagit version

        helm.add_repo(self._logger, namespace, 'https://dagster-io.github.io/helm')

        # TODO in DagsterDeploy we "Apply it and retrieve it again to make sure it has the "last-applied-configuration" annotation"
        user_deployments = get_key_of_config_map(namespace, 'dagster-user-code', 'user-deployments.yaml')
        user_code_deployments = user_deployments['deployments']
        deployment_names = [u['name'] for u in user_code_deployments]

        new_deployment: dict = {}
        # get usercode deployments
        # check if name is in deployment_names, replace test with actual name from project.yml
        is_new_deployment = new_deployment['name'] not in deployment_names

        # merge usercode, maybe do a copy?
        if is_new_deployment:
            user_code_deployments.append(new_deployment)
        else:
            for i, deployment in user_code_deployments:
                if deployment['name'] == new_deployment['name']:
                    user_code_deployments[i] = new_deployment

        # run "helm upgrade -i ... ...."
        deploy_result = deploy_helm_chart(self._logger, chart, step_input, builder.release_name)


        # TODO in DagsterDeploy we "Apply it and retrieve it again to make sure it has the "last-applied-configuration" annotation"
        workspace = get_key_of_config_map(namespace, 'dagster-workspace-yaml', 'workspace.yaml')
        workspace_names = [w['grpc_server'] for w in workspace['load_from']]
        is_new_server = new_deployment['name'] not in workspace_names

        if is_new_server:
            self._logger('Adding new server')
            new_workspace_servers_list = workspace['load_from']
            new_workspace_servers_list.append(new_deployment)

            helm.install()

        # TODO does this also need to be done if they are new?
        rollout_restart_deployment(namespace, "dagster-dagit")
        rollout_restart_deployment(namespace, "dagster-daemon")
        return None