"""Uploads static files to s3 and then deploys the docker image referring to the files on S3
 and produced in the build stage to Kubernetes, using HELM."""
import tempfile
from logging import Logger

from . import STAGE_NAME
from .kubernetes import DeployKubernetes
from .. import Step, Meta
from ..models import Input, Output, ArtifactType
from ...utilities.docker import (
    docker_copy,
    create_container,
    full_image_path_for_project,
)
from ...utilities.s3 import S3Client, S3ClientConfig

STATIC_FOLDER = "static"


class CloudFrontKubernetesDeploy(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger,
            Meta(
                name="CloudFront Kubernetes Deploy",
                description="uploads the build output to an s3 bucket",
                version="0.0.1",
                stage=STAGE_NAME,
            ),
            produced_artifact=ArtifactType.NONE,
            required_artifact=ArtifactType.DOCKER_IMAGE,
        )

    def execute(self, step_input: Input) -> Output:
        with tempfile.TemporaryDirectory() as tmp_folder:
            self.__copy_docker_assets(
                logger=self._logger, step_input=step_input, tmp_folder=tmp_folder
            )

            if not step_input.dry_run:
                self.__upload_to_s3(
                    logger=self._logger, step_input=step_input, tmp_folder=tmp_folder
                )

        return DeployKubernetes(self._logger).execute(step_input)

    @staticmethod
    def __copy_docker_assets(logger: Logger, step_input: Input, tmp_folder: str):
        """
        Copies the static assets from the docker image to a temp folder
        """
        full_image_path = full_image_path_for_project(step_input)
        container_path = f"{step_input.project.name}/{STATIC_FOLDER}"
        container = create_container(logger, full_image_path)
        docker_copy(
            logger=logger,
            container_path=container_path,
            dst_path=tmp_folder,
            container=container,
        )

    @staticmethod
    def __upload_to_s3(logger: Logger, step_input: Input, tmp_folder: str):
        """
        Creates an S3 client and uploads the static assets stored in the temp folder
        """
        logger.info("Creating S3 client")

        bucket_name = step_input.project.s3_bucket.bucket.get_value(
            step_input.run_properties.target
        )
        bucket_region = step_input.project.s3_bucket.region

        s3_config = S3ClientConfig(
            run_properties=step_input.run_properties,
            bucket_name=bucket_name,
            bucket_region=bucket_region,
        )
        s3_client = S3Client(logger, s3_config)

        logger.info(
            f"Uploading assets to '{s3_config.bucket_root_path}' in bucket '{s3_config.bucket_name}'"
        )
        s3_client.upload_directory(
            directory=tmp_folder, root_asset_location=STATIC_FOLDER
        )
        logger.info("Upload complete")
