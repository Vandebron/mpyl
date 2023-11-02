from pathlib import Path

from ruamel.yaml import YAML  # type: ignore

from src.mpyl.constants import BUILD_ARTIFACTS_FOLDER
from src.mpyl.projects.find import load_projects
from src.mpyl.stages.discovery import (
    find_invalidated_projects_for_stage,
    output_invalidated,
)
from src.mpyl.steps import Output
from src.mpyl.steps import build, test, deploy
from src.mpyl.utilities.repo import Revision
from tests import root_test_path, test_resource_path
from tests.test_resources import test_data
from tests.test_resources.test_data import TestStage

yaml = YAML()


class TestDiscovery:
    def test_should_find_invalidated_test_dependencies(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/service/file.py", "tests/some_file.txt"}
            projects = set(load_projects(repo.root_dir, repo.find_projects()))
            assert (
                len(
                    find_invalidated_projects_for_stage(
                        projects,
                        build.STAGE_NAME,
                        [Revision(0, "revision", touched_files)],
                    )
                )
                == 1
            )
            assert (
                len(
                    find_invalidated_projects_for_stage(
                        projects,
                        test.STAGE_NAME,
                        [Revision(0, "revision", touched_files)],
                    )
                )
                == 2
            )
            assert (
                len(
                    find_invalidated_projects_for_stage(
                        projects,
                        deploy.STAGE_NAME,
                        [Revision(0, "revision", touched_files)],
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
        invalidated = find_invalidated_projects_for_stage(
            projects,
            TestStage.build().name,
            [Revision(0, "hash", {"projects/job/file.py", "some_file.txt"})],
        )
        assert 1 == len(invalidated)

    def test_invalidation_logic(self):
        test_output = Path(
            test_resource_path / "deployment" / BUILD_ARTIFACTS_FOLDER / "test.yml"
        ).read_text(encoding="utf-8")
        output = yaml.load(test_output)
        assert not output.success, "output should not be successful"
        assert output_invalidated(None, "hash"), "should be invalidated if no output"
        assert output_invalidated(
            output, "hash"
        ), "should be invalidated if output is not successful"
        assert output_invalidated(
            Output(success=True, message="No artifact produced"), "hash"
        ), "should be invalidated if no artifact produced"

        output.success = True
        assert output_invalidated(
            output, "hash"
        ), "should be invalidated if hash doesn't match"
        assert not output_invalidated(
            output, "a2fcde18082e14a260195b26f7f5bfed9dc8fbb4"
        ), "should be valid if hash matches"

    def test_listing_override_files(self):
        with test_data.get_repo() as repo:
            touched_files = {"tests/projects/overriden-project/file.py"}
            projects = load_projects(repo.root_dir, repo.find_projects())
            assert len(projects) == 11
            projects_for_build = find_invalidated_projects_for_stage(
                projects, build.STAGE_NAME, [Revision(0, "revision", touched_files)]
            )
            projects_for_test = find_invalidated_projects_for_stage(
                projects, test.STAGE_NAME, [Revision(0, "revision", touched_files)]
            )
            projects_for_deploy = find_invalidated_projects_for_stage(
                projects, deploy.STAGE_NAME, [Revision(0, "revision", touched_files)]
            )
            assert len(projects_for_build) == 1
            assert len(projects_for_test) == 1
            assert len(projects_for_deploy) == 2
            assert projects_for_deploy.pop().deployment.kubernetes.port_mappings == {
                8088: 8088,
                8089: 8089,
            }
            # as the env variables are not key value pair, they are a bit tricky to merge
            # 1 in overriden-project and 1 in parent project
            # assert(len(projects_for_deploy.pop().deployment.properties.env) == 2)
