from src.mpyl.utilities.helm import convert_to_helm_release_name, get_name_suffix
from tests.test_resources import test_data


class TestHelm:
    def test_convert_to_helm_release_name(self):
        assert (
            convert_to_helm_release_name("MY_project", "-pr-1234")
            == "my-project-pr-1234"
        )
        assert convert_to_helm_release_name("my.project", "") == "my-project"

    def test_get_name_suffix_for_pr_target(self):
        assert get_name_suffix(test_data.RUN_PROPERTIES) == "-pr-1234"

    def test_get_name_suffix_for_prod_target(self):
        assert get_name_suffix(test_data.RUN_PROPERTIES_PROD) == ""
