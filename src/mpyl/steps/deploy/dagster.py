from logging import Logger

from .. import Step, Meta, ArtifactType, Input, Output
from ...project import Stage


class DagsterDeploy(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='Kubernetes Job Deploy',
            description='Deploy a job to k8s',
            version='0.0.1',
            stage=Stage.DEPLOY
        ), produced_artifact=ArtifactType.NONE, required_artifact=ArtifactType.DOCKER_IMAGE)

    # Deploys the docker image produced in the build stage as a Dagster user-code-deployment
    def execute(self, step_input: Input) -> Output:
        self._logger("To be implemented")

        # steps for dagster deploy (from DagsterDeploy.groovy)
        # namespace: dagster
        # checking dagster-dagit version

        # helm chart needs to be added
        # "helm repo add dagster https://dagster-io.github.io/helm"
        # "helm repo update"

        # user-code-configmap (dagster-user-code.yaml)

        # check for existing usercode deployment, remove it if there
        # if usercode deployment exists, merge/upsert configmaps (old and new)
        # create user code deployment (DagsterUtil)

        # write temp file? (might not be needed here anymore)
        # run "helm upgrade -i ... ...."

        # if usercode deployment existed already, we need to do a  rolling restart of the repo server
        # (kubectl rollout restart deployment ${deployment} --namespace ${namespace}

        # get dagster-workspace-yaml
        # run this 👇 for dagit and daemon (if newserver)
        # (kubectl rollout restart deployment ${deployment} --namespace ${namespace}



        pass