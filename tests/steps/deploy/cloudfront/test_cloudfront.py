import logging
from unittest.mock import patch
from mpyl.steps.deploy.cloudfront_kubernetes_deploy import CloudFrontKubernetesDeploy, STATIC_FOLDER
from src.mpyl.steps.models import Input
from tests.test_resources.test_data import get_cloudfront_project, RUN_PROPERTIES


class TestCloudFront:

    @patch('mpyl.steps.deploy.cloudfront_kubernetes_deploy.docker_copy')
    @patch('mpyl.steps.deploy.cloudfront_kubernetes_deploy.docker_image_tag')
    def test_copy_docker_assets_succeeds(self, mock_image_tag, mock_docker_copy):
        mock_image_tag.return_value = 'test_image'
        project = get_cloudfront_project()
        step_input = Input(project, RUN_PROPERTIES, None)

        logger = logging.getLogger()
        CloudFrontKubernetesDeploy.copy_docker_assets(logger, step_input=step_input, tmp_folder='tmp')

        mock_docker_copy.assert_called_once()
