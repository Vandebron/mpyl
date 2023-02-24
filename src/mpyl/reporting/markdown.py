"""
Markdown run result formatters
"""
import itertools

from junitparser import TestSuite

from ..project import Stage
from ..steps.models import ArtifactType
from ..steps.run import RunResult
from ..steps.steps import StepResult
from ..utilities.junit import TestRunSummary, to_test_suites, sum_suites


def summary_to_markdown(summary: TestRunSummary):
    return f":test_tube: {summary.tests} :x: {summary.failures} " \
           f":broken_heart: {summary.errors} :see_no_evil: {summary.skipped}"


def __to_oneliner(result: list[StepResult]):
    project_names = list(map(lambda r: r.project.name, result))
    return f'{", ".join(project_names)}'


def __collect_test_results(step_results: list[StepResult]) -> list[TestSuite]:
    test_artifacts = [res.output.produced_artifact for res in step_results if
                      (res.output.produced_artifact and
                       res.output.produced_artifact.artifact_type == ArtifactType.JUNIT_TESTS)]

    suites: list[list[TestSuite]] = list(map(to_test_suites, test_artifacts))
    flattened = list(itertools.chain(*suites))
    return flattened


def run_result_to_markdown(run_result: RunResult) -> str:
    result: str = ""

    for stage in Stage:
        step_results: list[StepResult] = run_result.results_for_stage(stage)
        if step_results:
            result += f"**{stage}** _{__to_oneliner(step_results)}_ \n"
            test_results = __collect_test_results(step_results)
            if test_results:
                result += to_markdown_test_report(test_results) + '\n'

    return result


def to_markdown_test_report(suites: list[TestSuite]):
    total_tests = sum_suites(suites)
    return f"{summary_to_markdown(total_tests)}"
