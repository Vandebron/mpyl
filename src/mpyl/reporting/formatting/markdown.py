"""
Markdown run result formatters
"""
import itertools
import operator
from typing import cast, Optional

from junitparser import TestSuite

from ...project import Stage, Project
from ...steps import Output, ArtifactType
from ...steps.deploy.k8s import DeployedHelmAppSpec
from ...steps.run import RunResult
from ...steps.steps import StepResult
from ...utilities.junit import (
    TestRunSummary,
    sum_suites,
    to_test_suites,
    JunitTestSpec,
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
        app_spec = cast(DeployedHelmAppSpec, output.produced_artifact.spec)
        url: Optional[str] = app_spec.url
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


def markdown_for_stage(run_result: RunResult, stage: Stage):
    step_results: list[StepResult] = run_result.results_for_stage(stage)
    plan: set[Project] = run_result.plan_for_stage(stage)
    if not step_results and not plan:
        return ""

    result = f"{stage.icon} {__to_oneliner(step_results, plan)}  \n"
    test_artifacts: dict[str, JunitTestSpec] = _collect_test_specs(step_results)
    test_results: dict[str, list[TestSuite]] = _collect_test_results(test_artifacts)

    if test_results:
        test_suites = list(
            itertools.chain.from_iterable([value for _, value in test_results.items()])
        )
        result += to_markdown_test_report(test_suites)
        unique_artifacts = _collect_unique_test_artifacts_with_url(test_artifacts)

        for unique_artifact in unique_artifacts:
            result += (
                f" [{unique_artifact.test_results_url_name}]"
                f"({unique_artifact.test_results_url})"
            )

        result += "  \n"

    return result


def run_result_to_markdown(run_result: RunResult) -> str:
    status_line: str = f"{run_result.status_line}  \n"
    return status_line + execution_plan_as_markdown(run_result)


def execution_plan_as_markdown(run_result: RunResult):
    result = ""
    exception = run_result.exception
    if exception:
        result += f"For _{exception.executor}_ on _{exception.project_name}_ at stage _{exception.stage}_ \n"
        result += f"\n\n{exception}\n\n"
    elif run_result.failed_result:
        failed = run_result.failed_result
        result += f"For _{failed.project.name}_ at stage _{failed.stage.name}_ \n"
        result += f"\n\n{run_result.failed_result.output.message}\n\n"
    for stage in run_result.run_properties.stages:
        result += markdown_for_stage(run_result, stage)
    return result


def to_markdown_test_report(suites: list[TestSuite]):
    total_tests = sum_suites(suites)
    return f"{summary_to_markdown(total_tests)}"


def _collect_test_specs(step_results: list[StepResult]) -> dict[str, JunitTestSpec]:
    return {
        res.output.produced_artifact.producing_step: cast(
            JunitTestSpec, res.output.produced_artifact.spec
        )
        for res in step_results
        if (
            res.output.produced_artifact
            and res.output.produced_artifact.artifact_type == ArtifactType.JUNIT_TESTS
        )
    }


def _collect_test_results(
    test_artifacts: dict[str, JunitTestSpec]
) -> dict[str, list[TestSuite]]:
    return {k: to_test_suites(v) for k, v in test_artifacts.items()}


def _collect_unique_test_artifacts_with_url(
    test_artifacts: dict[str, JunitTestSpec],
) -> list[JunitTestSpec]:
    unique_artifacts: list[JunitTestSpec] = []
    for step_name, test_artifact in test_artifacts.items():
        if test_artifact.test_results_url:
            duplicate_artifact = next(
                (
                    x
                    for x in unique_artifacts
                    if x.test_results_url == test_artifact.test_results_url
                ),
                None,
            )
            if not duplicate_artifact:
                test_artifact.test_results_url_name = step_name
                unique_artifacts.append(test_artifact)
            else:
                duplicate_artifact.test_results_url_name = "link"

    return unique_artifacts
