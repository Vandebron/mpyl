import os
from pathlib import Path
from unittest import mock

import pytest
from jsonschema import ValidationError

from src.mpyl.cli.commands.build.mpyl import find_build_set
from src.mpyl.project import load_project, Target
from src.mpyl.utilities.repo import Repository
from tests.test_resources import test_data
from tests import root_test_path


class TestMplSchema:
    resource_path = root_test_path / "test_resources"

    def test_schema_load(self):
        project = load_project(Path(""), self.resource_path / "test_project.yml")
        assert project.name == 'dockertest'
        assert project.maintainer, ['Marketplace' == 'Energy Trading']
        envs = project.deployment.properties.env

        simple_env = [x for x in envs if x.key == 'SOME_ENV'].pop()
        assert simple_env.key == 'SOME_ENV'
        assert simple_env.get_value(Target.ACCEPTANCE) == 'Acceptance'
        assert simple_env.get_value(Target.PRODUCTION) == 'Production'

        secret_env = [x for x in project.deployment.properties.sealed_secret if x.key == 'SOME_SECRET_ENV'].pop()
        assert secret_env.get_value(Target.PULL_REQUEST).startswith('AgCA5/qvMMp'), "should start with"

        assert project.dependencies.build == {'test/docker/'}
        assert project.dependencies.test == set()

        assert project.deployment.kubernetes.port_mappings == {8080: 8080}
        assert project.deployment.kubernetes.liveness_probe.path.get_value(Target.ACCEPTANCE) == '/health'
        assert not project.deployment.kubernetes.metrics.enabled, "metrics should be disabled"

        host = project.deployment.traefik.hosts[0]
        assert host.host.get_value(Target.PULL_REQUEST_BASE) == 'Host(`payments.test.vdbinfra.nl`)'
        assert host.tls.get_value(Target.PULL_REQUEST_BASE) == 'le-custom-prod-wildcard-cert'

    def test_schema_load_validation(self):
        with pytest.raises(ValidationError) as exc:
            load_project(Path(""), self.resource_path / "test_project_invalid.yml")
        assert exc.value.message == "'maintainer' is a dependency of 'deployment'"

    def test_pre_build_fast_validation(self):
        """Assert that run_build fast fails on project.yml validation for all projects before starting the build(s)"""

        with mock.patch.object(Repository, 'find_projects') as find_projects_mocked:
            find_projects_mocked.return_value = {
                'tests/projects/job/deployment/project.yml', 'tests/projects/sbt-service/deployment/project.yml',
                'tests/projects/ephemeral/deployment/project.yml', 'tests/projects/service/deployment/project.yml',
                'tests/projects/spark-job/deployment/project.yml', 'tests/test_resources/test_project_invalid.yml'
            }
            os.chdir(root_test_path.parent)
            repo = test_data.get_repo()

            with pytest.raises(ValidationError) as exc:
                find_build_set(repo, [], True)
            assert exc.value.message == "'maintainer' is a dependency of 'deployment'"

    def test_target_by_value(self):
        target = Target('PullRequest')
        assert target == Target.PULL_REQUEST
