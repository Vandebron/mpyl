"""A client to connect to an S3 bucket"""

import pathlib
from dataclasses import dataclass
from typing import Optional
from logging import Logger
from os import walk
import boto3
from botocore.exceptions import ClientError

from ...project import Project
from ...steps.models import RunProperties


@dataclass
class S3ClientConfig:
    service_name = 's3'
    region_name = 'eu-central-1'
    access_key_id: Optional[str]
    secret_access_key: Optional[str]
    bucket_name: str
    bucket_root_path: str

    def __init__(self, run_properties: RunProperties, project: Project):
        s3_connection_info = run_properties.config.get('s3', None)
        self.access_key_id = s3_connection_info.get('accessKeyId')
        self.secret_access_key = s3_connection_info.get('secretAccessKey')
        self.bucket_name = self.__get_bucket_name(run_properties, project)
        self.bucket_root_path = run_properties.versioning.identifier

    @staticmethod
    def __get_bucket_name(run_properties: RunProperties, project: Project) -> str:
        """
        Retrieves the S3 bucket name from the step input
        """
        s3_config = project.s3_bucket
        if s3_config is None or s3_config.bucket is None:
            raise AttributeError("deployment.s3.bucket property should be set")
        return s3_config.bucket.get_value(run_properties.target)


class S3Client:

    def __init__(self, logger: Logger, config: S3ClientConfig):
        """
        Creates a client that provides a wrapper for uploading a directory to an S3 bucket

        :param config: the S3 client config containing the necessary credentials and bucket information
        """
        self._client = boto3.client(service_name=config.service_name,
                                    region_name=config.region_name,
                                    aws_access_key_id=config.access_key_id,
                                    aws_secret_access_key=config.secret_access_key)
        self._buck_name = config.bucket_name
        self._bucket_root_path = config.bucket_root_path
        self._logger = logger

    def upload_directory(self, directory: str, dry_run: bool = False):
        """
        Uploads all files in a directory and its subdirectories to the S3 bucket

        Note: boto3 does not provide a sync method, so we have to walk the directory and upload each file individually

        :param dry_run: if true, the upload will be skipped
        :param directory: the name of the root directory containing the content to upload
        """
        walks = walk(directory)
        for path, _, filenames in walks:
            for filename in filenames:
                src_path = f'{path}/{filename}'
                dst_path = self.create_file_dst(root_path=self._bucket_root_path, file_path=path, filename=filename)
                if not dry_run:
                    self.upload_file(src_path=src_path, dst_path=dst_path)

    @staticmethod
    def create_file_dst(root_path: str, file_path: str, filename: str):
        """
        Creates the bucket key for a given file based on its relative path and the given bucket root path
        i.e. /root/path/relative/path/filename

        The first 2 parts of the path are excluded as they are an auto created tmp directory of the form
        '/tmp/asVx3sd/...'

        :param root_path: the root path on the bucket
        :param file_path: the relative path of the file
        :param filename: the name of the file
        :return: the full destination path/key in the s3 bucket
        """
        path_parts = pathlib.Path(file_path).parts
        non_tmp_parts = path_parts[3:]
        relative_path = f"{'/'.join(filter(None, non_tmp_parts))}"
        return f'{root_path}/{relative_path}/{filename}' if non_tmp_parts else f'{root_path}/{filename}'

    def upload_file(self, src_path: str, dst_path: str):
        """
        Uploads an individual file to the S3 bucket

        :param src_path: the local relative path of the file
        :param dst_path: the destination path within the bucket
        :return: whether the upload was successful

        """
        self._logger.debug(f"Uploading to bucket: {self._buck_name}")
        self._logger.debug(f"Uploading file at '{src_path}' to '{dst_path}'")

        try:
            self._client.upload_file(src_path, self._buck_name, dst_path)
        except ClientError as exc:
            self._logger.warning(f'Unexpected exception uploading file: {src_path} - {exc}')
            raise exc
