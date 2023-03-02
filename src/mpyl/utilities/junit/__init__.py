"""Wrapper around `junitparser`"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from junitparser import JUnitXml, TestSuite
from python_on_whales import docker

from ...project import Project
from ...steps.models import Artifact, ArtifactType, Input, input_to_artifact

TEST_OUTPUT_PATH_KEY = 'test_output_path'


@dataclass(frozen=True)
class TestRunSummary:
    tests: int
    failures: int
    errors: int
    skipped: int

    @property
    def is_success(self):
        return self.errors == 0 and self.failures == 0


def to_test_suites(artifact: Artifact) -> list[TestSuite]:
    if artifact.artifact_type != ArtifactType.JUNIT_TESTS:
        raise ValueError(f'Artifact {artifact} should be of type {ArtifactType.JUNIT_TESTS}')
    junit_result_path = artifact.spec[TEST_OUTPUT_PATH_KEY]

    xml = JUnitXml()
    for file_name in [fn for fn in os.listdir(junit_result_path) if fn.endswith('.xml')]:
        xml += JUnitXml.fromfile(Path(junit_result_path, file_name))

    suites = [TestSuite.fromelem(s) for s in xml]
    return sorted(suites, key=lambda s: s.time)


def sum_suites(suites: list[TestSuite]) -> TestRunSummary:
    return TestRunSummary(tests=sum(s.tests for s in suites), failures=sum(s.failures for s in suites),
                          errors=sum(s.failures for s in suites), skipped=sum(s.skipped for s in suites))


def extract_test_results(project: Project, tag, step_input: Input) -> Artifact:
    test_result_path = Path(project.target_path, "test_results")
    shutil.rmtree(test_result_path, ignore_errors=True)
    Path(test_result_path).mkdir(parents=True, exist_ok=True)

    container_id = docker.create(tag).id
    docker.copy(f'{container_id}:/{project.test_report_path}/.', test_result_path)

    return input_to_artifact(artifact_type=ArtifactType.JUNIT_TESTS, step_input=step_input,
                             spec={TEST_OUTPUT_PATH_KEY: f'{test_result_path}'})
