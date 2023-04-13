"""Wrapper around `junitparser`"""
import os
from dataclasses import dataclass
from pathlib import Path

from junitparser import JUnitXml, TestSuite

from ...steps.models import Artifact, ArtifactType

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
        xml += JUnitXml.fromfile(Path(junit_result_path, file_name).as_posix())

    suites = [TestSuite.fromelem(s) for s in xml]
    return sorted(suites, key=lambda s: s.time)


def sum_suites(suites: list[TestSuite]) -> TestRunSummary:
    return TestRunSummary(tests=sum(s.tests for s in suites), failures=sum(s.failures for s in suites),
                          errors=sum(s.errors for s in suites), skipped=sum(s.skipped for s in suites))
