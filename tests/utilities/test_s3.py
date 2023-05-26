from unittest.mock import patch
import logging
import pytest
from botocore.exceptions import ClientError
from mpyl.utilities.s3 import S3Client


class TestS3:

    @patch('boto3.client')
    def test_create_client_succeeds(self, mock_boto3_client):
        s3_config = {'s3': {'accessKeyId': 'testId', 'secretAccessKey': 'testKey'}}

        S3Client(logger=logging.getLogger(), config=s3_config, bucket_name='test', root_path='root')
        mock_boto3_client.assert_called_once()

    def test_create_client_fails(self):
        s3_config1 = {}
        s3_config2 = {'s3': {}}
        s3_config3 = {'s3': {'accessKeyId': 'testId'}}
        s3_config4 = {'s3': {'secretAccessKey': 'testKey'}}
        s3_config5 = {'s3': {'accessKeyId': ''}}
        s3_config6 = {'s3': {'secretAccessKey': ''}}

        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config1, bucket_name='test', root_path='root')
        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config2, bucket_name='test', root_path='root')
        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config3, bucket_name='test', root_path='root')
        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config4, bucket_name='test', root_path='root')
        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config5, bucket_name='test', root_path='root')
        with pytest.raises(ValueError, match='S3 configuration not set'):
            S3Client(logger=logging.getLogger(), config=s3_config6, bucket_name='test', root_path='root')

    @patch('boto3.s3.inject.upload_file')
    def test_upload_file_succeeds(self, mock_boto_upload_file):
        s3_config = {'s3': {'accessKeyId': 'testId', 'secretAccessKey': 'testKey'}}
        s3_client = S3Client(logger=logging.getLogger(), config=s3_config, bucket_name='test', root_path='root')

        upload_successful = s3_client.upload_file(src_path='tests/test_resources/test_file.txt',
                                                  dst_path='test_file.txt')

        mock_boto_upload_file.assert_called_once_with('tests/test_resources/test_file.txt', 'test', 'test_file.txt')
        assert upload_successful

    @patch('boto3.s3.inject.upload_file')
    def test_upload_file_fails(self, mock_boto_upload_file):
        mock_boto_upload_file.side_effect = ClientError(operation_name='test', error_response={})

        s3_config = {'s3': {'accessKeyId': 'testId', 'secretAccessKey': 'testKey'}}
        s3_client = S3Client(logger=logging.getLogger(), config=s3_config, bucket_name='test', root_path='root')

        upload_successful = s3_client.upload_file(src_path='tests/test_resources/test_file.txt',
                                                  dst_path='test_file.txt')

        mock_boto_upload_file.assert_called_once_with('tests/test_resources/test_file.txt', 'test', 'test_file.txt')
        assert not upload_successful

    def test_create_dst_path_succeeds(self):
        bucket_path1 = S3Client.create_file_dst(root_path='root', file_path='tmp', filename='filename.js')
        bucket_path2 = S3Client.create_file_dst(root_path='root', file_path='tmp/js', filename='filename.js')
        bucket_path3 = S3Client.create_file_dst(root_path='root', file_path='tmp/css', filename='filename.css')
        bucket_path4 = S3Client.create_file_dst(root_path='root', file_path='tmp/assets', filename='filename.jpg')
        bucket_path5 = S3Client.create_file_dst(root_path='root', file_path='tmp/assets/docs', filename='filename.pdf')

        assert bucket_path1 == 'root/filename.js'
        assert bucket_path2 == 'root/js/filename.js'
        assert bucket_path3 == 'root/css/filename.css'
        assert bucket_path4 == 'root/assets/filename.jpg'
        assert bucket_path5 == 'root/assets/docs/filename.pdf'
