import contextlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import RUN_ARTIFACTS_FOLDER
from src.mpyl.project import load_project, Stage
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import (
    find_projects_to_execute,
    is_project_cached_for_stage,
    is_file_a_dependency,
)
from src.mpyl.steps import ArtifactType
from src.mpyl.steps import Output
from src.mpyl.steps import build, test, deploy
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.steps.models import Artifact
from src.mpyl.utilities.docker import DockerImageSpec
from src.mpyl.utilities.repo import Changeset
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import TestStage

yaml = YAML()

HASHED_CHANGES_OF_JOB = (
    "e993ba4f2b2ae2c4840e1eed1414baa812932319d332b0d169365b0885ec2d6c"
)


@contextlib.contextmanager
def _caching_for(
    project: str,
    stage: Stage = TestStage.build(),
    hashed_contents: str = HASHED_CHANGES_OF_JOB,
):
    path = f"tests/projects/{project}/deployment/{RUN_ARTIFACTS_FOLDER}"

    if not os.path.isdir(path):
        os.makedirs(path)

    try:
        Output(
            success=True,
            message="a test output",
            produced_artifact=Artifact(
                artifact_type=ArtifactType.DOCKER_IMAGE,
                revision="a git revision",
                producing_step="a step",
                spec=DockerImageSpec(image="docker-image-path"),
                hash=hashed_contents,
            ),
        ).write(
            target_path=path,
            stage=stage.name,
        )
        yield path
    finally:
        shutil.rmtree(path)


class TestDiscovery:
    logger = logging.getLogger(__name__)
    steps = StepsCollection(logger=logger)
    project_paths = [
        "tests/projects/job/deployment/project.yml",
        "tests/projects/service/deployment/project.yml",
        "tests/projects/sbt-service/deployment/project.yml",
    ]
    projects = set(load_projects(root_test_path.parent, project_paths))

    def _helper_find_projects_to_execute(
        self,
        files_touched: dict[str, str],
        stage: Stage = TestStage.build(),
    ):
        return find_projects_to_execute(
            logger=self.logger,
            all_projects=self.projects,
            stage=stage.name,
            changeset=Changeset(
                sha="a git SHA",
                _files_touched=files_touched,
            ),
            steps=self.steps,
        )

    def test_changed_files_from_file(self):
        with test_data.get_repo() as repo:
            changeset = repo.changes_from_file(
                self.logger, "tests/test_resources/repository/changed_files.json"
            )
            assert len(changeset._files_touched) == 1
            assert "tests/projects/job/src/hello-world.py" in changeset._files_touched

    def test_find_projects_to_execute_for_each_stage(self):
        with test_data.get_repo() as repo:
            changeset = Changeset(
                sha="revision",
                _files_touched={
                    "tests/projects/service/file.py": "A",
                    "tests/some_file.txt": "A",
                },
            )
            projects = set(load_projects(repo.root_dir, repo.find_projects()))
            assert (
                len(
                    find_projects_to_execute(
                        self.logger,
                        projects,
                        build.STAGE_NAME,
                        changeset,
                        self.steps,
                    )
                )
                == 1
            )
            assert (
                len(
                    find_projects_to_execute(
                        self.logger,
                        projects,
                        test.STAGE_NAME,
                        changeset,
                        self.steps,
                    )
                )
                == 2
            )
            assert (
                len(
                    find_projects_to_execute(
                        self.logger,
                        projects,
                        deploy.STAGE_NAME,
                        changeset,
                        self.steps,
                    )
                )
                == 1
            )

    def test_stage_with_files_changed(self):
        project_executions = self._helper_find_projects_to_execute(
            files_touched={
                "tests/projects/job/deployment/project.yml": "M",
            },
        )
        assert len(project_executions) == 1
        job_execution = next(p for p in project_executions if p.project.name == "job")
        assert not job_execution.cached
        assert job_execution.hashed_changes == HASHED_CHANGES_OF_JOB

    def test_stage_with_files_changed_and_existing_cache(self):
        with _caching_for(project="job"):
            project_executions = self._helper_find_projects_to_execute(
                files_touched={
                    "tests/projects/job/deployment/project.yml": "M",
                },
            )
            assert len(project_executions) == 1
            job_execution = next(
                p for p in project_executions if p.project.name == "job"
            )
            assert job_execution.cached
            assert job_execution.hashed_changes == HASHED_CHANGES_OF_JOB

    def test_stage_with_files_changed_but_filtered(self):
        with _caching_for(project="job"):
            project_executions = self._helper_find_projects_to_execute(
                files_touched={
                    "tests/projects/job/deployment/project.yml": "D",
                },
            )
            assert len(project_executions) == 1
            job_execution = next(
                p for p in project_executions if p.project.name == "job"
            )
            assert not job_execution.cached
            # all modified files are filtered out, no hash in current run
            assert not job_execution.hashed_changes

    def test_stage_with_build_dependency_changed(self):
        with _caching_for(project="job"):
            project_executions = self._helper_find_projects_to_execute(
                files_touched={
                    "tests/projects/sbt-service/src/main/scala/vandebron/mpyl/Main.scala": "M"
                },
            )

            # both job and sbt-service should be executed
            assert len(project_executions) == 2

            job_execution = next(
                p for p in project_executions if p.project.name == "job"
            )

            # a build dependency changed, so this project should always run
            assert not job_execution.cached
            # no files changes in the current run
            assert not job_execution.hashed_changes

    def test_stage_with_test_dependency_changed(self):
        project_executions = self._helper_find_projects_to_execute(
            files_touched={"tests/projects/service/file.py": "M"},
        )

        # job should not be executed because it wasn't modified and service is only a test dependency
        assert len(project_executions) == 1
        assert not {p for p in project_executions if p.project.name == "job"}

    def test_stage_with_files_changed_and_dependency_changed(self):
        with _caching_for(project="job"):
            project_executions = self._helper_find_projects_to_execute(
                files_touched={
                    "tests/projects/job/deployment/project.yml": "M",
                    "tests/projects/sbt-service/src/main/scala/vandebron/mpyl/Main.scala": "M",
                },
            )

            # both job and sbt-service should be executed
            assert len(project_executions) == 2

            job_execution = next(
                p for p in project_executions if p.project.name == "job"
            )

            # a build dependency changed, so this project should always run even if there's a cached version available
            assert not job_execution.cached
            assert job_execution.hashed_changes == HASHED_CHANGES_OF_JOB

    def test_should_correctly_check_root_path(self):
        assert not is_file_a_dependency(
            self.logger,
            load_project(
                test_resource_path,
                Path("../projects/sbt-service/deployment/project.yml"),
            ),
            stage="build",
            path="projects/sbt-service-other/file.py",
            steps=self.steps,
        )

    def test_is_stage_cached(self):
        hashed_changes = "a generated test hash"

        test_artifact = Artifact(
            artifact_type=ArtifactType.DOCKER_IMAGE,
            revision="revision",
            producing_step="step",
            spec=DockerImageSpec(image="image"),
            hash=hashed_changes,
        )

        def create_test_output(
            success: bool = True,
            artifact: Optional[Artifact] = test_artifact,
        ):
            return Output(
                success=success, message="an output message", produced_artifact=artifact
            )

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="deploy",
            output=create_test_output(),
            hashed_changes=hashed_changes,
        ), "should not be cached if the stage is deploy"

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=None,
            hashed_changes=hashed_changes,
        ), "should not be cached if no output"

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=create_test_output(success=False),
            hashed_changes=hashed_changes,
        ), "should not be cached if output is not successful"

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=create_test_output(artifact=None),
            hashed_changes=hashed_changes,
        ), "should not be cached if no artifact produced"

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=create_test_output(),
            hashed_changes=None,
        ), "should not be cached if there are no changes in the current run"

        assert not is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=create_test_output(),
            hashed_changes="a hash that doesn't match",
        ), "should not be cached if hash doesn't match"

        assert is_project_cached_for_stage(
            logger=self.logger,
            project="a test project",
            stage="a test stage",
            output=create_test_output(),
            hashed_changes=hashed_changes,
        ), "should be cached if hash matches"

    def test_listing_override_files(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/overriden-project/file.py": "A"}
            projects = load_projects(repo.root_dir, repo.find_projects())
            assert len(projects) == 11
            projects_for_build = find_projects_to_execute(
                self.logger,
                projects,
                build.STAGE_NAME,
                Changeset("revision", touched_files),
                self.steps,
            )
            projects_for_test = find_projects_to_execute(
                self.logger,
                projects,
                test.STAGE_NAME,
                Changeset("revision", touched_files),
                self.steps,
            )
            projects_for_deploy = find_projects_to_execute(
                self.logger,
                projects,
                deploy.STAGE_NAME,
                Changeset("revision", touched_files),
                self.steps,
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
