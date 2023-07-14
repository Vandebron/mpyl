"""
Step to deploy a dagster user code repository to k8s
"""
from logging import Logger
from typing import List


from .k8s import helm, get_key_of_config_map, rollout_restart_deployment, cluster_config
from ..models import RunProperties
from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage, Project, Target, get_env_variables
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

    def __to_user_code_deployment(self, project: Project, run_properties: RunProperties):
        env_variables = get_env_variables(project, run_properties.target)
        name_prefix = f'pr-{run_properties.versioning.pr_number}-' if run_properties.target == Target.PULL_REQUEST else ''
        return {'deployments': [{
            'dagsterApiGrpcArgs': [
                "--python-file",
                project.dagster.repo
            ],
            'env': env_variables,
            'envSecrets': [],
            'image': {
                'pullPolicy': 'Always',
                'imagePullSecrets': [
                    {
                        'name': 'bigdataregistry'
                    }
                ],
                'tag': run_properties.versioning.identifier,
                'repository': f'bigdataregistry.azurecr.io/{project.name}'
            },
            'includeConfigInLaunchedRuns': {
                'enabled': True
            },
            'name': f'{name_prefix}{project.name}',
            'port': 3030
        }]}

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        namespace = 'dagster'
        context = cluster_config(step_input.run_properties.target, step_input.run_properties).context

        # get dagster version command
        version = '1.3.10'
        self._logger.info(f'Dagster Version: {version}')
        # checking dagster-dagit version

        # TODO is there a global way for installing this depenendency?
        helm.add_repo(self._logger, namespace, 'https://dagster-io.github.io/helm')

        deploy_set = find_deploy_set(RepoConfig.from_config(step_input.run_properties.config), step_input.run_properties.versioning.tag)
        # we have the possiblity to have more than one project to be deployed
        # we could bulk upsert them here, or we run the upsertion per project
        user_code_deployments: List[dict] = []

        # TODO we dont need create user_deployment.yaml anymore -> we can provide a values.yaml to the helm upgrade command
        for project in deploy_set.projects_to_deploy:
            user_code_deployments.append(self.__to_user_code_deployment(project, step_input.run_properties))
            # conversion of project.yml to user-code chart
            # Chartbuilder might not be needed, or needs adjustment to accommodate for appending to existing chart

        deploy_results = []
        for deployment in user_code_deployments:
            result = helm.install_with_values_yaml(
                self._logger,
                step_input,
                deployment,
                'uc-test',
                'dagster/dagster-user-deployments',
                'dagster',
                context)
            deploy_results.append(result)

        # DagsterDeploy we "Apply it and retrieve it again to make sure it has the last-applied-configuration annotation"
        workspace = get_key_of_config_map(context, namespace, 'dagster-workspace-yaml', 'workspace.yaml')
        workspace_names = [w['grpc_server'] for w in workspace['load_from']]
        # is_new_server = user_code_deployments['name'] not in workspace_names

        # if is_new_server:
        #     self._logger.info('Adding new server')
        #     new_workspace_servers_list = workspace['load_from']
        #     new_workspace_servers_list.append(user_code_deployments)

        #     # kubectl apply with updated workspace.yaml

        #     rollout_restart_deployment(namespace, "dagster-dagit")
        #     rollout_restart_deployment(namespace, "dagster-daemon")

        return deploy_results[0]
