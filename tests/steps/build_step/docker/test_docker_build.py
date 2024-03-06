from src.mpyl.steps.build.docker_build import BuildDocker


class TestDockerBuild:
    def test_substitutes_correctly(self):
        substituted_value = BuildDocker.substitute_pr_number(
            original_value="test-{PR-NUMBER}.test.vdbinfra.nl",
            pr_number=1234
        )
        assert substituted_value == "test-1234.test.vdbinfra.nl"

    def test_does_not_substitute_normal_values(self):
        substituted_value = BuildDocker.substitute_pr_number(
            original_value="test.backend.vdbinfra.nl",
            pr_number=1234
        )
        assert substituted_value == "test.backend.vdbinfra.nl"

    def test_does_not_substitute_non_prs(self):
        substituted_value = BuildDocker.substitute_pr_number(
            original_value="vandebron.nl",
            pr_number=None
        )
        assert substituted_value == "vandebron.nl"
