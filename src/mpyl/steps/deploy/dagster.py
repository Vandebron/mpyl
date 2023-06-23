"""
Step to deploy a dagster user code repository to k8s
"""
from logging import Logger

from .k8s import helm, get_key_of_config_map, rollout_restart_deployment, cluster_config
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage, Project
from ...stages.discovery import find_deploy_set
from ...utilities.repo import RepoConfig


class DeployDagster(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Dagster Deploy',
            description='Deploy a dagster user code repository to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def __to_user_code_deployment(self, project: Project):
        return {
            'dagsterApiGrpcArgs': [
                "--python-file",
                project.name
            ],
            'envSecrets': [],
            'image': {
                'pullPolicy': 'Always',
                'imagePullSecrets': [],
                'tag': ''
            },
            'name': project.name,  # make PR distinction
            'port': 3030
        }

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        namespace = 'dagster'
        context = cluster_config(step_input).context

        # get dagster version command
        version = '1.3.10'
        self._logger.info(f'Dagster Version: {version}')
        self._logger.info(f'Namespace will be overwritten and project will be pushed to {namespace}')
        # namespace: dagster
        # checking dagster-dagit version

        helm.add_repo(self._logger, namespace, 'https://dagster-io.github.io/helm')

        deploy_set = find_deploy_set(RepoConfig.from_config(step_input.run_properties.config))
        print(deploy_set.projects_to_deploy)
        new_user_code_deployments = []
        for project in deploy_set.projects_to_deploy:
            new_user_code_deployments.append(self.__to_user_code_deployment(project))
        new_user_code_deployment = new_user_code_deployments[0]
        # conversion of project.yml to user-code chart

        # DagsterDeploy we Apply it and retrieve it again to make sure it has the last-applied-configuration annotation
        user_deployments = get_key_of_config_map(context, namespace, 'dagster-user-code', 'user-deployments.yaml')
        user_code_deployments = user_deployments['deployments']
        # deployment_names = [u['name'] for u in user_code_deployments]

        is_new_deployment = False  # new_deployment['name'] not in deployment_names

        # merge usercode, maybe do a copy?
        if is_new_deployment:
            user_code_deployments.append(new_user_code_deployment)
        else:
            for i, deployment in enumerate(user_code_deployments):
                if deployment['name'] == new_user_code_deployment['name']:
                    user_code_deployments[i] = new_user_code_deployment

        # deploy_result = deploy_helm_chart(self._logger, chart, step_input, builder.release_name)

        if is_new_deployment:
            rollout_restart_deployment(namespace,
                                       f"user-code-dagster-user-deployments-${new_user_code_deployment['name']}")

        # DagsterDeploy we Apply it and retrieve it again to make sure it has the last-applied-configuration annotation
        workspace = get_key_of_config_map(context, namespace, 'dagster-workspace-yaml', 'workspace.yaml')
        # workspace_names = [w['grpc_server'] for w in workspace['load_from']]
        is_new_server = False  # new_user_code_deployment['name'] not in workspace_names

        if is_new_server:
            self._logger.info('Adding new server')
            new_workspace_servers_list = workspace['load_from']
            new_workspace_servers_list.append(new_user_code_deployment)

            rollout_restart_deployment(namespace, "dagster-dagit")
            rollout_restart_deployment(namespace, "dagster-daemon")

        return Output(False, "Still implementing")
