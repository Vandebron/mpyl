"""Wrapper around `junitparser`"""

import os
from dataclasses import dataclass
from junitparser import JUnitXml, TestSuite

from ...steps.models import Artifact, ArtifactType


@dataclass(frozen=True)
class TestRunSummary:
    tests: int
    failures: int
    errors: int
    skipped: int


def to_test_suites(artifact: Artifact):
    if artifact.artifact_type != ArtifactType.JUNIT_TESTS:
        raise ValueError(f'Artifact {artifact} should be of type {ArtifactType.JUNIT_TESTS}')
    junit_result_path = artifact.spec['test_output_path']

    xml = JUnitXml()
    for file_name in [fn for fn in os.listdir(junit_result_path) if fn.endswith('.xml')]:
        xml += JUnitXml.fromfile(junit_result_path / file_name)

    suites = [TestSuite.fromelem(s) for s in xml]
    return sorted(suites, key=lambda s: s.time)


def sum_suites(suites: list[TestSuite]) -> TestRunSummary:
    return TestRunSummary(tests=sum(s.tests for s in suites), failures=sum(s.failures for s in suites),
                          errors=sum(s.failures for s in suites), skipped=sum(s.skipped for s in suites))
