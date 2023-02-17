"""
Simple run result formatters
"""
import os
from dataclasses import dataclass

from junitparser import JUnitXml, TestSuite

from ..project import Stage
from ..steps.models import Artifact, ArtifactType
from ..steps.run import RunResult


def to_string(run_result: RunResult) -> str:
    result: str = ""
    for stage in Stage:
        run_results = run_result.results_for_stage(stage)
        if run_results:
            result += f"Stage {stage.name}\n"
            for res in run_results:
                result += f"{res.timestamp} - {res.project.name} - {res.stage} - success: {res.output.success} \n"
    return result


@dataclass(frozen=True)
class TestRunSummary:
    tests: int
    failures: int
    errors: int
    skipped: int


def sum_suites(suites: list[TestSuite]) -> TestRunSummary:
    return TestRunSummary(tests=sum(s.tests for s in suites), failures=sum(s.failures for s in suites),
                          errors=sum(s.failures for s in suites), skipped=sum(s.skipped for s in suites))


def to_test_suites(artifact: Artifact):
    if artifact.artifact_type != ArtifactType.JUNIT_TESTS:
        raise ValueError(f'Artifact {artifact} should be of type {ArtifactType.JUNIT_TESTS}')
    junit_result_path = artifact.spec['test_output_path']

    xml = JUnitXml()
    for file_name in [fn for fn in os.listdir(junit_result_path) if fn.endswith('.xml')]:
        xml += JUnitXml.fromfile(junit_result_path / file_name)

    suites = [TestSuite.fromelem(s) for s in xml]
    return sorted(suites, key=lambda s: s.time)


def to_test_report(artifact: Artifact):
    test_result = ""
    suites = to_test_suites(artifact)
    total_tests = sum_suites(suites)
    test_result += f"{total_tests} \n\n"
    for suite in suites:
        test_result += f"Suite {suite.name}\n"
        for case in suite:
            test_result += f"Case {case.name} \n"

    return test_result
