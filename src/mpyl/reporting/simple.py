import os

from ..steps.models import Artifact, ArtifactType
from ...mpyl import Stage
from ...mpyl.steps.run import RunResult
from junitparser import JUnitXml, TestSuite, TestCase


def to_string(run_result: RunResult) -> str:
    result: str = ""
    for stage in Stage:
        run_results = run_result.results_for_stage(stage)
        if run_results:
            result += f"Stage {stage.name}\n"
            for res in run_results:
                result += f"{res.timestamp} - {res.project.name} - {res.stage} - success: {res.output.success} \n"
    return result


def to_test_report(artifact: Artifact):
    if artifact.artifact_type != ArtifactType.JUNIT_TESTS:
        raise ValueError(f'Artifact {artifact} should be of type {ArtifactType.JUNIT_TESTS.name}')
    junit_result_path = artifact.spec['test_output_path']

    test_result: str = ""
    xml = JUnitXml()
    for file_name in [fn for fn in os.listdir(junit_result_path) if fn.endswith('.xml')]:
        xml += JUnitXml.fromfile(junit_result_path / file_name)

    for suite in (TestSuite.fromelem(s) for s in xml):
        test_result += f"Suite {suite.name}\n"
        for case in suite:
            test_result += f"Case {case.name} \n"
    return test_result
