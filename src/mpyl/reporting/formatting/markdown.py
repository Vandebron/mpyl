"""
Markdown run result formatters
"""
import operator
import itertools

from junitparser import TestSuite

from ...project import Stage, Project
from ...steps import Output, ArtifactType
from ...steps.models import Artifact
from ...steps.run import RunResult
from ...steps.steps import StepResult
from ...utilities.junit import (
    TestRunSummary,
    sum_suites,
    TEST_RESULTS_URL_KEY,
    TEST_RESULTS_URL_NAME_KEY,
    to_test_suites,
)


def summary_to_markdown(summary: TestRunSummary):
    return (
        f"🧪 {summary.tests} ❌ {summary.failures} "
        f"💔 {summary.errors} 🙈 {summary.skipped}"
    )


def __add_link_if_service(name: str, output: Output) -> str:
    if (
        output.produced_artifact
        and output.produced_artifact.artifact_type == ArtifactType.DEPLOYED_HELM_APP
    ):
        url = output.produced_artifact.spec.get("url")
        if url:
            return f"[{name}]({url})"

    return name


def wrap_project_name(proj: Project, result: list[StepResult]):
    project_name = proj.name
    encapsulation = "_"
    found_result = next((r for r in result if r.project.name == project_name), None)
    if found_result:
        project_name = __add_link_if_service(project_name, found_result.output)
        encapsulation = "*" if found_result.output.success else "~~"

    return f"{encapsulation}{project_name}{encapsulation}"


def __to_oneliner(result: list[StepResult], plan: set[Project]) -> str:
    project_names: list[str] = []
    if plan:
        sorted_plan = sorted(plan, key=operator.attrgetter("name"))
        for proj in sorted_plan:
            project_names.append(wrap_project_name(proj, result))
    else:
        project_names = list(map(lambda r: f"_{r.project.name}_", result))

    return f'{", ".join(project_names)}'


def stage_to_icon(stage: Stage):
    if stage == Stage.BUILD:
        return "🏗️"
    if stage == Stage.TEST:
        return "📋"
    if stage == Stage.DEPLOY:
        return "🚀"
    if stage == Stage.POST_DEPLOY:
        return "🦺"
    return "➡️"


def markdown_for_stage(run_result: RunResult, stage: Stage):
    step_results: list[StepResult] = run_result.results_for_stage(stage)
    plan: set[Project] = run_result.plan_for_stage(stage)
    if not step_results and not plan:
        return ""

    result = f"{stage_to_icon(stage)} {__to_oneliner(step_results, plan)}  \n"
    test_artifacts = _collect_test_artifacts(step_results)
    test_results = _collect_test_results(test_artifacts)

    if test_results:
        result += to_markdown_test_report(test_results)
        unique_artifacts = _collect_unique_test_artifacts_with_url(test_artifacts)

        for unique_artifact in unique_artifacts:
            result += (
                f" [{unique_artifact.spec[TEST_RESULTS_URL_NAME_KEY]}]"
                f"({unique_artifact.spec[TEST_RESULTS_URL_KEY]})"
            )

        result += "  \n"

    return result


def run_result_to_markdown(run_result: RunResult) -> str:
    status_line: str = f"{run_result.status_line}  \n"
    return status_line + execution_plan_as_markdown(run_result)


def execution_plan_as_markdown(run_result):
    result = ""
    exception = run_result.exception
    if exception:
        result += f"For _{exception.executor}_ on _{exception.project_name}_ at _{exception.stage}_ \n"
        result += f"\n\n{exception}\n\n"
    elif run_result.failed_result:
        failed = run_result.failed_result
        result += f"For _{failed.project.name}_ at _{failed.stage}_ \n"
        result += f"\n\n{run_result.failed_result.output.message}\n\n"
    for stage in Stage:
        result += markdown_for_stage(run_result, stage)
    return result


def to_markdown_test_report(suites: list[TestSuite]):
    total_tests = sum_suites(suites)
    return f"{summary_to_markdown(total_tests)}"


def _collect_test_artifacts(step_results: list[StepResult]) -> list[Artifact]:
    return [
        res.output.produced_artifact
        for res in step_results
        if (
            res.output.produced_artifact
            and res.output.produced_artifact.artifact_type == ArtifactType.JUNIT_TESTS
        )
    ]


def _collect_test_results(test_artifacts: list[Artifact]) -> list[TestSuite]:
    suites: list[list[TestSuite]] = list(map(to_test_suites, test_artifacts))

    return list(itertools.chain(*suites))


def _collect_unique_test_artifacts_with_url(
    test_artifacts: list[Artifact],
) -> list[Artifact]:
    unique_artifacts: list[Artifact] = []
    for test_artifact in test_artifacts:
        if (
            TEST_RESULTS_URL_KEY in test_artifact.spec
            and test_artifact.spec[TEST_RESULTS_URL_KEY] != ""
        ):
            duplicate_artifact = next(
                (
                    x
                    for x in unique_artifacts
                    if x.spec[TEST_RESULTS_URL_KEY]
                    == test_artifact.spec[TEST_RESULTS_URL_KEY]
                ),
                None,
            )
            if not duplicate_artifact:
                test_artifact.spec[
                    TEST_RESULTS_URL_NAME_KEY
                ] = test_artifact.producing_step
                unique_artifacts.append(test_artifact)
            else:
                duplicate_artifact.spec[TEST_RESULTS_URL_NAME_KEY] = "link"

    return unique_artifacts
