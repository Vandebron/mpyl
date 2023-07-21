from mpyl.utilities.helm import convert_name_to_helm_release_name


class TestHelm:
    def test_convert_to_helm_release_name(self):
        assert (
            convert_name_to_helm_release_name("my-project", "-pr-1234") == "mp-pr-1234"
        )
        assert convert_name_to_helm_release_name("my-project", "") == "mp"
