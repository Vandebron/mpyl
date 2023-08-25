from mpyl.utilities.helm import convert_to_helm_release_name, shorten_name


class TestHelm:
    def test_convert_to_helm_release_name(self):
        assert (
            convert_to_helm_release_name("MY_project", "-pr-1234")
            == "my-project-pr-1234"
        )
        assert convert_to_helm_release_name("my.project", "") == "my-project"

    def test_shorten_name(self):
        assert shorten_name("my-project") == "mp"
