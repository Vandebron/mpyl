"""
Markdown run result formatters
"""

from junitparser import TestSuite

from ...project import Stage, Project
from ...steps.run import RunResult
from ...steps.steps import StepResult, collect_test_results
from ...utilities.junit import TestRunSummary, sum_suites


def summary_to_markdown(summary: TestRunSummary):
    return f"🧪 {summary.tests} ❌ {summary.failures} " \
           f"💔 {summary.errors} 🙈 {summary.skipped}"


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


def stage_to_icon(stage: Stage):
    if stage == Stage.BUILD:
        return '🏗️ '
    if stage == Stage.TEST:
        return '🧪'
    if stage == Stage.DEPLOY:
        return '🚀'
    return '➡️'


def run_result_to_markdown(run_result: RunResult) -> str:
    result: str = f'{run_result.status_line}  \n' if run_result.is_finished and run_result.run_plan else ""
    if run_result.exception:
        result += f"\n```\n{run_result.exception}\n```\n"

    for stage in Stage:
        step_results: list[StepResult] = run_result.results_for_stage(stage)
        plan: set[Project] = run_result.plan_for_stage(stage)
        if step_results or plan:
            result += f"{stage_to_icon(stage)}  {__to_oneliner(step_results, plan)}  \n"
            test_results = collect_test_results(step_results)
            if test_results:
                result += to_markdown_test_report(
                    test_results) + f' [link]({run_result.run_properties.details.tests_url}) \n'

    return result


def to_markdown_test_report(suites: list[TestSuite]):
    total_tests = sum_suites(suites)
    return f"{summary_to_markdown(total_tests)}"
