"""Wrapper around `junitparser`"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from junitparser import JUnitXml, TestSuite
from ruamel.yaml import yaml_object, YAML

from ...steps.models import ArtifactSpec

yaml = YAML()


@yaml_object(yaml)
@dataclass
class JunitTestSpec(ArtifactSpec):
    yaml_tag = "!JunitTestSpec"
    test_output_path: str
    test_results_url: Optional[str] = None
    test_results_url_name: Optional[str] = None


@dataclass(frozen=True)
class TestRunSummary:
    __test__ = False
    tests: int
    failures: int
    errors: int
    skipped: int

    @property
    def is_success(self):
        return self.errors == 0 and self.failures == 0


def to_test_suites(artifact: JunitTestSpec) -> list[TestSuite]:
    junit_result_path = artifact.test_output_path

    xml = JUnitXml()
    for file_name in [
        fn for fn in os.listdir(junit_result_path) if fn.endswith(".xml")
    ]:
        xml += JUnitXml.fromfile(Path(junit_result_path, file_name).as_posix())

    suites = [TestSuite.fromelem(s) for s in xml]
    return sorted(suites, key=lambda s: s.time)


def sum_suites(suites: list[TestSuite]) -> TestRunSummary:
    return TestRunSummary(
        tests=sum(s.tests for s in suites),
        failures=sum(s.failures for s in suites),
        errors=sum(s.errors for s in suites),
        skipped=sum(s.skipped for s in suites),
    )
