"""
Simple run result formatters
"""
from typing import cast

from ...project import Stage
from ...steps.models import ArtifactType
from ...steps.run import RunResult
from ...utilities.junit import to_test_suites, sum_suites, JunitTestSpec


def to_string(run_result: RunResult) -> str:
    result: str = ""
    for stage in Stage:
        run_results = run_result.results_for_stage(stage)
        if run_results:
            result += f"Stage {stage.name}\n"
            for res in run_results:
                result += f"{res.timestamp} - {res.project.name} - {res.stage} - success: {res.output.success} \n"
                artifact = res.output.produced_artifact
                if artifact and artifact.artifact_type == ArtifactType.JUNIT_TESTS:
                    result += to_test_report(cast(JunitTestSpec, artifact.spec))

    return result


def to_test_report(artifact: JunitTestSpec) -> str:
    """Gather the first test suites and test cases. Output is truncated to around 200 lines to not overwhelm Github"""
    test_result = []
    suites = to_test_suites(artifact)
    total_tests = sum_suites(suites)
    test_result.append(f"{total_tests} \n\n")
    for suite in suites:
        test_result.append(f"Suite {suite.name}\n")
        if len(test_result) > 200:
            test_result.append("  ... output truncated\n")
            break
        for case in suite:
            test_result.append(f"  Case {case.name} \n")
    return "".join(test_result)
