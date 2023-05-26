""" Step that uploads static files to s3 and then deploys the docker image produced in the build stage to Kubernetes,
using HELM."""
from logging import Logger
from typing import Dict
from .kubernetes import DeployKubernetes
from .. import Step, Meta
from ...project import Stage
from ..models import Input, Output, ArtifactType
from ...utilities.docker import docker_image_tag, git_tag, docker_copy
from ...utilities.filesystem import delete_directory
from ...utilities.s3 import S3Client

TMP_FOLDER = 'tmp'
STATIC_FOLDER = 'static'


class CloudFrontKubernetesDeploy(Step):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger, Meta(
            name='CloudFront Kubernetes Deploy',
            description='uploads the build output to an s3 bucket',
            version='0.0.1',
            stage=Stage.DEPLOY,
        ), produced_artifact=ArtifactType.DOCKER_IMAGE, required_artifact=ArtifactType.DOCKER_IMAGE)

    def execute(self, step_input: Input) -> Output:
        bucket_name = self.get_bucket_name(step_input)
        image_name = docker_image_tag(step_input)
        container_path = f'{step_input.project.name}/{STATIC_FOLDER}'
        tag = git_tag(step_input)

        docker_copy(logger=self._logger, container_path=container_path, dst_path=TMP_FOLDER,
                    image_name=image_name)
        self.upload_to_s3(run_config=step_input.run_properties.config, bucket_name=bucket_name, src_path=TMP_FOLDER,
                          bucket_root_path=tag)
        delete_directory(logger=self._logger, dir_name=TMP_FOLDER)

        return DeployKubernetes(self._logger).execute(step_input)

    def upload_to_s3(self, run_config: Dict, bucket_name: str, src_path: str, bucket_root_path: str):
        """
        Creates an S3 client and uploads the static assets stored in the temp folder

        :param run_config: the config containing S3 info
        :param bucket_name: the name of the bucket
        :param src_path: the local path of the directory to upload
        :param bucket_root_path: the destination path in the bucket
        :return:
        """
        s3_client = S3Client(self._logger, config=run_config, bucket_name=bucket_name,
                             root_path=bucket_root_path)
        self._logger.info(f"Uploading assets to '{bucket_root_path}' in bucket '{bucket_name}'")
        s3_client.upload_directory(src_path)
        self._logger.info('Upload complete')

    @staticmethod
    def get_bucket_name(step_input: Input) -> str:
        """
        Retrieves the S3 bucket name from the step input

        """
        s3_config = step_input.project.s3_bucket
        if s3_config is None or s3_config.bucket is None:
            raise AttributeError("deployment.s3.bucket field should be set")
        return s3_config.bucket.get_value(step_input.run_properties.target)
