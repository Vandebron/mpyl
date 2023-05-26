"""A client to connect to an S3 bucket"""

import pathlib
from typing import Dict
from logging import Logger
from os import walk
import boto3
from botocore.exceptions import ClientError


class S3Client:

    def __init__(self, logger: Logger, config: Dict, bucket_name: str, root_path: str):
        """
        Creates a client that provides a wrapper for uploading a directory to an S3 bucket

        :param config: the mpyl_config containing an AWS access key ID and secret key
        :param bucket_name: the name of the bucket this client will operate on
        :param root_path: the root path on the bucket in which files will be uploaded to
        """
        s3_config = config.get('s3', None)
        if not s3_config or not s3_config.get('accessKeyId') or not s3_config.get('secretAccessKey'):
            raise ValueError('S3 configuration not set')

        self._client = boto3.client(service_name='s3',
                                    region_name='eu-central-1',
                                    aws_access_key_id=s3_config['accessKeyId'],
                                    aws_secret_access_key=s3_config['secretAccessKey'])
        self._bucket_name = bucket_name
        self._root_path = root_path
        self._logger = logger

    def upload_directory(self, directory: str):
        """
        Uploads all files in a directory and its subdirectories to the S3 bucket

        Note: boto3 does not provide a sync method, so we have to walk the directory and upload each file individually

        :param directory: the name of the root directory containing the content to upload
        """
        walks = walk(directory)
        for path, _, filenames in walks:
            for filename in filenames:
                src_path = f'{path}/{filename}'
                dst_path = self.create_file_dst(root_path=self._root_path, file_path=path, filename=filename)
                self.upload_file(src_path=src_path, dst_path=dst_path)

    @staticmethod
    def create_file_dst(root_path: str, file_path: str, filename: str):
        """
        Creates the bucket key for a given file based on its relative path and the given bucket root path
        i.e. /root/path/relative/path/filename

        The first part of the path is excluded as it is a temporary directory

        :param root_path: the root path on the bucket
        :param file_path: the relative path of the file
        :param filename: the name of the file
        :return: the full destination path/key in the s3 bucket
        """
        _, *tail = pathlib.Path(file_path).parts
        relative_path = f"{'/'.join(filter(None, tail))}"
        return f'{root_path}/{relative_path}/{filename}' if tail else f'{root_path}/{filename}'

    def upload_file(self, src_path: str, dst_path: str) -> bool:
        """
        Uploads an individual file to the S3 bucket

        :param src_path: the local relative path of the file
        :param dst_path: the destination path within the bucket
        :return: whether the upload was successful

        """
        self._logger.debug(f"Uploading to bucket: {self._bucket_name}")
        self._logger.debug(f"Uploading file at '{src_path}' to '{dst_path}'")

        try:
            self._client.upload_file(src_path, self._bucket_name, dst_path)
            return True
        except ClientError as exc:
            self._logger.warning(f'Unexpected exception uploading file: {src_path} - {exc}')
            return False
