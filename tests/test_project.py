import os
from pathlib import Path

import pytest
from jsonschema import ValidationError

from src.mpyl.project import load_project, Target
from tests import root_test_path


class TestMplSchema:
    resource_path = root_test_path / "test_resources"

    def test_schema_load(self):
        os.environ["CHANGE_ID"] = "123"
        project = load_project(Path(""), self.resource_path / "test_project.yml")

        assert project.name == "dockertest"
        assert project.maintainer, ["Marketplace" == "Energy Trading"]
        envs = project.deployment.properties.env

        simple_env = [x for x in envs if x.key == "SOME_ENV"].pop()
        assert simple_env.key == "SOME_ENV"
        assert simple_env.get_value(Target.ACCEPTANCE) == "Acceptance"
        assert simple_env.get_value(Target.PRODUCTION) == "Production"

        secret_env = [
            x
            for x in project.deployment.properties.sealed_secret
            if x.key == "SOME_SECRET_ENV"
        ].pop()
        assert secret_env.get_value(Target.PULL_REQUEST).startswith(
            "AgCA5/qvMMp"
        ), "should start with"

        assert project.dependencies.build == {"test/docker/"}
        assert project.dependencies.test == set()

        assert project.deployment.kubernetes.port_mappings == {8080: 80}
        assert (
            project.deployment.kubernetes.liveness_probe.path.get_value(
                Target.ACCEPTANCE
            )
            == "/health"
        )
        assert project.deployment.kubernetes.metrics.enabled

        host = project.deployment.traefik.hosts[0]
        assert (
            host.host.get_value(Target.PULL_REQUEST_BASE) == "Host(`payments.test.nl`)"
        )
        assert (
            host.host.get_value(Target.PULL_REQUEST)
            == "Host(`payments-{PR-NUMBER}.test.nl`)"
        )
        assert (
            host.tls.get_value(Target.PULL_REQUEST_BASE)
            == "le-custom-prod-wildcard-cert"
        )

        assert (
            project.deployment.properties.env[2].all
            == "minimalService.{namespace}.svc.cluster.local"
        )

    def test_schema_load_validation(self):
        with pytest.raises(ValidationError) as exc:
            load_project(Path(""), self.resource_path / "test_project_invalid.yml")
        assert exc.value.message == "'maintainer' is a dependency of 'deployment'"

    def test_target_by_value(self):
        target = Target(Target.PULL_REQUEST)
        assert target == Target.PULL_REQUEST
