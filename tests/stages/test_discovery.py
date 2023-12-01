import logging
from pathlib import Path

from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import BUILD_ARTIFACTS_FOLDER
from src.mpyl.project import Project
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import (
    find_invalidated_projects_for_stage,
    _to_changed_files,
    ChangedFile,
    _is_newer_than_artifact,
    _is_output_invalid,
)
from src.mpyl.steps import Output
from src.mpyl.steps import build, test, deploy
from src.mpyl.steps.collection import StepsCollection
from src.mpyl.utilities.repo import Revision
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import TestStage

yaml = YAML()


class TestDiscovery:
    steps = StepsCollection(logger=logging.getLogger())
    revisions = [
        Revision(0, "hash1", {"projects/job/file.py", "some_file.txt"}),
        Revision(1, "hash2", {"projects/job/file.py"}),
        Revision(2, "hash3", {"other_file.txt"}),
    ]

    def find(self, stage: str, projects: set[Project], touched_files: set[str]):
        return {
            project.name
            for project in find_invalidated_projects_for_stage(
                projects,
                stage,
                [Revision(0, "revision", touched_files)],
                self.steps,
            )
        }

    def test_should_check_if_newer_than_artifact(self):
        assert _is_newer_than_artifact("hash1", "hash3", self.revisions) is True
        assert _is_newer_than_artifact("hash3", "hash1", self.revisions) is False
        assert _is_newer_than_artifact("nonexistent", "hash1", self.revisions) is True
        assert _is_newer_than_artifact("hash2", "nonexistent", self.revisions) is True

    def test_should_take_latest_revision_per_path(self):
        changed = _to_changed_files(self.revisions)
        assert changed == {
            ChangedFile(path="other_file.txt", revision="hash3"),
            ChangedFile(path="projects/job/file.py", revision="hash2"),
            ChangedFile(path="some_file.txt", revision="hash1"),
        }

    def test_should_find_invalidated_test_dependencies(self):
        touched_files = {"tests/projects/service/file.py", "tests/some_file.txt"}
        projects = set(
            load_projects(
                test_data.get_repo().root_dir, test_data.get_repo().find_projects()
            )
        )
        assert self.find(build.STAGE_NAME, projects, touched_files) == {"nodeservice"}
        assert self.find(test.STAGE_NAME, projects, touched_files) == {
            "nodeservice",
            "job",
        }
        assert self.find(deploy.STAGE_NAME, projects, touched_files) == {
            "nodeservice",
        }

    def test_should_find_invalidated_build_dependencies(self):
        touched_files = {
            "tests/projects/sbt-service/src/main/scala/vandebron/mpyl/Main.scala",
        }
        projects = set(
            load_projects(
                test_data.get_repo().root_dir, test_data.get_repo().find_projects()
            )
        )
        assert self.find(build.STAGE_NAME, projects, touched_files) == {
            "job",
            "sbtservice",
        }
        assert self.find(test.STAGE_NAME, projects, touched_files) == {
            "sbtservice",
        }
        assert self.find(deploy.STAGE_NAME, projects, touched_files) == {
            "job",
            "sbtservice",
        }

    def test_should_find_invalidated_dependencies(self):
        project_paths = [
            "projects/job/deployment/project.yml",
            "projects/service/deployment/project.yml",
            "projects/sbt-service/deployment/project.yml",
        ]
        projects = set(load_projects(root_test_path, project_paths))
        invalidated = find_invalidated_projects_for_stage(
            projects,
            TestStage.build().name,
            [Revision(0, "hash", {"projects/job/file.py", "some_file.txt"})],
            self.steps,
        )
        assert 1 == len(invalidated)

    def test_invalidation_logic(self):
        test_output = Path(
            test_resource_path / "deployment" / BUILD_ARTIFACTS_FOLDER / "test.yml"
        ).read_text(encoding="utf-8")
        output = yaml.load(test_output)
        assert not output.success, "output should not be successful"
        assert _is_output_invalid(
            None, [], "revision"
        ), "should be invalidated if no output"
        assert _is_output_invalid(
            output, [], "hash"
        ), "should be invalidated if output is not successful"
        assert _is_output_invalid(
            Output(success=True, message="No artifact produced"), [], "hash"
        ), "should be invalidated if no artifact produced"

        output.success = True
        assert _is_output_invalid(
            output, [], "hash"
        ), "should be invalidated if hash doesn't match"

        file_revision = "a2fcde18082e14a260195b26f7f5bfed9dc8fbb4"
        revisions = [Revision(0, file_revision, {"some_file.txt"})]
        assert not _is_output_invalid(
            output, revisions, file_revision
        ), "should be valid if hash matches"

    def test_listing_override_files(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/overriden-project/file.py"}
            projects = load_projects(repo.root_dir, repo.find_projects())
            assert len(projects) == 13
            projects_for_build = self.find(build.STAGE_NAME, projects, touched_files)
            projects_for_test = self.find(test.STAGE_NAME, projects, touched_files)

            projects_for_deploy = find_invalidated_projects_for_stage(
                projects,
                deploy.STAGE_NAME,
                [Revision(0, "revision", touched_files)],
                self.steps,
            )
            assert len(projects_for_build) == 1
            assert len(projects_for_test) == 1
            assert len(projects_for_deploy) == 2
            assert projects_for_deploy.pop().kubernetes.port_mappings == {
                8088: 8088,
                8089: 8089,
            }
            # as the env variables are not key value pair, they are a bit tricky to merge
            # 1 in overriden-project and 1 in parent project
            # assert(len(projects_for_deploy.pop().deployment.properties.env) == 2)
