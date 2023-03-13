"""
Markdown run result formatters
"""
import itertools

from junitparser import TestSuite

from ...project import Stage, Project
from ...steps.models import ArtifactType
from ...steps.run import RunResult
from ...steps.steps import StepResult
from ...utilities.junit import TestRunSummary, to_test_suites, sum_suites


def summary_to_markdown(summary: TestRunSummary):
    return f":test_tube: {summary.tests} :x: {summary.failures} " \
           f":broken_heart: {summary.errors} :see_no_evil: {summary.skipped}"


def __to_oneliner(result: list[StepResult], plan: set[Project]) -> str:
    project_names: list[str] = []
    if plan:
        for proj in plan:
            found_result = next((r for r in result if r.project.name == proj.name), None)
            if found_result:
                project_names.append(f'*{proj.name}*' if found_result.output.success else f'~~{proj.name}~~')
            else:
                project_names.append(f'_{proj.name}_')
    else:
        project_names = list(map(lambda r: f'_{r.project.name}_', result))

    return f'{", ".join(sorted(project_names))}'


def __collect_test_results(step_results: list[StepResult]) -> list[TestSuite]:
    test_artifacts = [res.output.produced_artifact for res in step_results if
                      (res.output.produced_artifact and
                       res.output.produced_artifact.artifact_type == ArtifactType.JUNIT_TESTS)]

    suites: list[list[TestSuite]] = list(map(to_test_suites, test_artifacts))
    flattened = list(itertools.chain(*suites))
    return flattened


def stage_to_icon(stage: Stage):
    if stage == Stage.BUILD:
        return 'building_construction'
    if stage == Stage.TEST:
        return 'test_tube'
    if stage == Stage.DEPLOY:
        return 'rocket'
    return 'arrow_right'


def run_result_to_markdown(run_result: RunResult) -> str:
    result: str = ""

    for stage in Stage:
        step_results: list[StepResult] = run_result.results_for_stage(stage)
        plan: set[Project] = run_result.plan_for_stage(stage)
        if step_results or plan:
            result += f":{stage_to_icon(stage)}: {__to_oneliner(step_results, plan)} \n"
            test_results = __collect_test_results(step_results)
            if test_results:
                result += to_markdown_test_report(
                    test_results) + f' [link]({run_result.run_properties.details.tests_url}) \n'

    return result


def to_markdown_test_report(suites: list[TestSuite]):
    total_tests = sum_suites(suites)
    return f"{summary_to_markdown(total_tests)}"
