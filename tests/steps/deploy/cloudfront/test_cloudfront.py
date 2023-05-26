from mpyl.steps.deploy.cloudfront_kubernetes_deploy import CloudFrontKubernetesDeploy
from src.mpyl.steps.models import Input
from tests.test_resources.test_data import get_cloudfront_project, RUN_PROPERTIES


class TestCloudFront:

    def test_get_bucket_name(self):
        project = get_cloudfront_project()
        step_input = Input(project, RUN_PROPERTIES, None)
        bucket_name = CloudFrontKubernetesDeploy.get_bucket_name(step_input)
        assert bucket_name == 'test-website-assets'
