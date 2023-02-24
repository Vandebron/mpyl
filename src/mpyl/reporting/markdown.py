"""
Markdown run result formatters
"""

from src.mpyl.project import Stage
from src.mpyl.steps.models import ArtifactType, Artifact
from src.mpyl.steps.run import RunResult
from src.mpyl.utilities.junit import TestRunSummary, to_test_suites, sum_suites


def summary_to_markdown(summary: TestRunSummary):
    return f":test_tube: {summary.tests} :x: {summary.failures} " \
           f":broken_heart: {summary.errors} :see_no_evil: {summary.skipped}"


def run_result_to_markdown(run_result: RunResult) -> str:
    result: str = ""
    for stage in Stage:
        run_results = run_result.results_for_stage(stage)
        if run_results:
            result += f"{stage}\n"
            for res in run_results:
                result += f"{res.project.name} - {res.stage} - success: {res.output.success} \n"
                artifact = res.output.produced_artifact
                if artifact and artifact.artifact_type == ArtifactType.JUNIT_TESTS:
                    result += to_markdown_test_report(artifact)

    return result


def to_markdown_test_report(artifact: Artifact):
    test_result = ""
    suites = to_test_suites(artifact)
    total_tests = sum_suites(suites)
    test_result += f"{summary_to_markdown(total_tests)} \n\n"

    return test_result
