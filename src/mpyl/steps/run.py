"""
Accumulate `mpyl.steps.run.RunResult` from executed `mpyl.steps.step.Step`
"""

import operator
from typing import Optional

from .models import RunProperties
from .executor import StepResult, ExecutionException
from ..project import Stage
from ..run_plan import RunPlan


class RunResult:
    _run_plan: RunPlan
    _results: list[StepResult]
    _run_properties: RunProperties
    _exception: Optional[ExecutionException]

    def __init__(self, run_properties: RunProperties):
        self._run_properties = run_properties
        self._run_plan = run_properties.run_plan
        self._exception = None
        self._results = []

    @property
    def status_line(self) -> str:
        if self._exception:
            return "❗ Failed with exception"
        if self.is_in_progress:
            return "🛠️ Building"
        if not self.has_results:
            return "🦥 Nothing to do"
        if self._results_success():
            return "✅ Successful"

        return "❌ Failed"

    @property
    def failed_results(self) -> Optional[list[StepResult]]:
        failed_results = list((r for r in self._results if not r.output.success))

        return failed_results if len(failed_results) > 0 else None

    @property
    def progress_fraction(self) -> float:
        unfinished = 0
        finished = 0
        for stage, project_executions in self.run_plan.selected_plan.items():
            finished_project_names = set(
                map(lambda r: r.project.name, self.results_for_stage(stage))
            )
            for project_execution in project_executions:
                if (
                    project_execution.name in finished_project_names
                    or project_execution.cached
                ):
                    finished += 1
                else:
                    unfinished += 1

        total = unfinished + finished
        if total == 0:
            return 0.0

        return 1.0 - (unfinished / total)

    @property
    def exception(self) -> Optional[ExecutionException]:
        return self._exception

    @exception.setter
    def exception(self, exception: ExecutionException):
        self._exception = exception

    @property
    def run_properties(self) -> RunProperties:
        return self._run_properties

    @property
    def run_plan(self) -> RunPlan:
        return self._run_plan

    def has_projects_to_run(self, include_cached_projects: bool = True) -> bool:
        return self.run_plan.has_projects_to_run(include_cached_projects)

    @property
    def results(self) -> list[StepResult]:
        return self._results

    def append(self, result: StepResult):
        self._results.append(result)

    def extend(self, results: list[StepResult]):
        self._results.extend(results)

    def update_run_plan(self, run_plan: RunPlan):
        self._run_plan.update(run_plan)

    @property
    def is_success(self):
        if self._exception:
            return False
        return self._results_success()

    @property
    def is_finished(self):
        return self.progress_fraction == 1.0

    @property
    def has_results(self):
        return len(self._results) > 0

    @property
    def is_in_progress(self):
        return (
            self.run_plan.has_projects_to_run(include_cached_projects=False)
            and self.is_success
            and not self.is_finished
        )

    def _results_success(self):
        return not self.has_results or all(r.output.success for r in self._results)

    @staticmethod
    def sort_chronologically(results: list[StepResult]) -> list[StepResult]:
        return sorted(results, key=operator.attrgetter("timestamp"))

    def results_for_stage(self, stage: Stage) -> list[StepResult]:
        return RunResult.sort_chronologically(
            [res for res in self._results if res.stage == stage]
        )
