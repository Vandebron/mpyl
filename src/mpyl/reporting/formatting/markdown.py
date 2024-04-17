"""
Markdown run result formatters
"""
import operator
from typing import cast, Optional

from ...project import Stage
from ...project_execution import ProjectExecution
from ...steps import Output, ArtifactType
from ...steps.deploy.k8s import DeployedHelmAppSpec
from ...steps.run import RunResult
from ...steps.steps import StepResult
from ...utilities.junit import TestRunSummary, JunitTestSpec


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


def wrap_project_name(project_execution: ProjectExecution, result: list[StepResult]):
    project_name = project_execution.name
    encapsulation = "_"
    found_result = next((r for r in result if r.project.name == project_name), None)
    if found_result:
        project_name = __add_link_if_service(project_name, found_result.output)
        encapsulation = "*" if found_result.output.success else "~~"

    return f"{encapsulation}{project_name}{' (cached)' if project_execution.cached else ''}{encapsulation}"


def __to_oneliner(result: list[StepResult], plan: set[ProjectExecution]) -> str:
    project_names: list[str] = []
    if plan:
        sorted_plans = sorted(plan, key=operator.attrgetter("name"))
        for project_execution in sorted_plans:
            project_names.append(wrap_project_name(project_execution, result))
    else:
        project_names = list(map(lambda r: f"_{r.project.name}_", result))

    return f'{", ".join(project_names)}'


def markdown_for_stage(run_result: RunResult, stage: Stage):
    step_results: list[StepResult] = run_result.results_for_stage(stage)
    plan = run_result.plan_for_stage(stage)
    if not step_results and not plan:
        return ""

    result = f"{stage.icon} {stage.name.capitalize()}:  \n{__to_oneliner(step_results, plan)}  \n"
    test_artifacts: dict[str, JunitTestSpec] = _collect_test_specs(step_results)
    test_results: dict[str, TestRunSummary] = _collect_test_results(test_artifacts)

    if test_results:
        test_summaries = [value for _, value in test_results.items()]
        combined_summary = TestRunSummary(
            tests=sum(s.tests for s in test_summaries),
            failures=sum(s.failures for s in test_summaries),
            errors=sum(s.errors for s in test_summaries),
            skipped=sum(s.skipped for s in test_summaries),
        )
        result += f"{summary_to_markdown(combined_summary)}"
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
    elif run_result.failed_results:
        failed_projects = ", ".join(
            set(failed.project.name for failed in run_result.failed_results)
        )
        failed_stage = next(failed.stage.name for failed in run_result.failed_results)
        failed_outputs = ". \n\n".join(
            [failed.output.message for failed in run_result.failed_results]
        )
        result += f"For _{failed_projects}_ at stage _{failed_stage}_ \n"
        result += f"\n\n{failed_outputs}\n\n"
    for stage in run_result.run_properties.stages:
        result += markdown_for_stage(run_result, stage)
    if result == "":
        return "🤷 Nothing to do"
    return result


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
) -> dict[str, TestRunSummary]:
    return {
        k: v.test_results_summary
        for k, v in test_artifacts.items()
        if v.test_results_summary
    }


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
