import logging
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML  # type: ignore

from src.mpyl.project import load_project
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import (
    build_project_executions,
    is_stage_cached,
    is_dependency_touched,
)
from src.mpyl.steps import ArtifactType
from src.mpyl.steps import Output
from src.mpyl.steps import build, test, deploy
from src.mpyl.steps.models import Artifact
from src.mpyl.utilities.docker import DockerImageSpec
from src.mpyl.utilities.repo import Changeset
from tests import root_test_path
from tests.test_resources import test_data
from tests.test_resources.test_data import TestStage

yaml = YAML()


class TestDiscovery:
    logger = logging.getLogger(__name__)

    def test_should_find_invalidated_test_dependencies(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/service/file.py", "tests/some_file.txt"}
            projects = set(load_projects(repo.root_dir, repo.find_projects()))
            assert (
                len(
                    build_project_executions(
                        self.logger,
                        projects,
                        build.STAGE_NAME,
                        Changeset("revision", touched_files),
                    )
                )
                == 1
            )
            assert (
                len(
                    build_project_executions(
                        self.logger,
                        projects,
                        test.STAGE_NAME,
                        Changeset("revision", touched_files),
                    )
                )
                == 2
            )
            assert (
                len(
                    build_project_executions(
                        self.logger,
                        projects,
                        deploy.STAGE_NAME,
                        Changeset("revision", touched_files),
                    )
                )
                == 1
            )

    def test_should_find_invalidated_dependencies(self):
        project_paths = [
            "projects/job/deployment/project.yml",
            "projects/service/deployment/project.yml",
            "projects/sbt-service/deployment/project.yml",
        ]
        projects = set(load_projects(root_test_path, project_paths))
        invalidated = build_project_executions(
            self.logger,
            projects,
            TestStage.build().name,
            Changeset("hash", {"projects/job/file.py", "some_file.txt"}),
        )
        assert 1 == len(invalidated)

    def test_should_correctly_check_root_path(self):
        assert not is_dependency_touched(
            self.logger,
            project=load_project(
                root_test_path, Path("projects/sbt-service/deployment/project.yml")
            ),
            stage="build",
            path="projects/sbt-service-other/file.py",
        )

    def test_is_stage_cached(self):
        cache_key = "a generated test hash"

        test_artifact = Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE,
            revision="revision",
            producing_step="step",
            spec=DockerImageSpec(image="image"),
            hash=cache_key,
        )

        def create_test_output(
            success: bool = True,
            artifact: Optional[Artifact] = test_artifact,
        ):
            return Output(
                success=success, message="an output message", produced_artifact=artifact
            )

        assert not is_stage_cached(
            output=None, cache_key=cache_key
        ), "should not be cached if no output"

        assert not is_stage_cached(
            output=create_test_output(success=False), cache_key=cache_key
        ), "should not be cached if output is not successful"

        assert not is_stage_cached(
            output=create_test_output(artifact=None), cache_key=cache_key
        ), "should not be cached if no artifact produced"

        assert not is_stage_cached(
            output=create_test_output(), cache_key="a hash that doesn't match"
        ), "should not be cached if hash doesn't match"

        assert is_stage_cached(
            output=create_test_output(), cache_key=cache_key
        ), "should be cached if hash matches"

    def test_listing_override_files(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/overriden-project/file.py"}
            projects = load_projects(repo.root_dir, repo.find_projects())
            assert len(projects) == 13
            projects_for_build = build_project_executions(
                self.logger,
                projects,
                build.STAGE_NAME,
                Changeset("revision", touched_files),
            )
            projects_for_test = build_project_executions(
                self.logger,
                projects,
                test.STAGE_NAME,
                Changeset("revision", touched_files),
            )
            projects_for_deploy = build_project_executions(
                self.logger,
                projects,
                deploy.STAGE_NAME,
                Changeset("revision", touched_files),
            )
            assert len(projects_for_build) == 1
            assert len(projects_for_test) == 1
            assert len(projects_for_deploy) == 2
            assert projects_for_deploy.pop().project.kubernetes.port_mappings == {
                8088: 8088,
                8089: 8089,
            }
            # as the env variables are not key value pair, they are a bit tricky to merge
            # 1 in overriden-project and 1 in parent project
            # assert(len(projects_for_deploy.pop().deployment.properties.env) == 2)
