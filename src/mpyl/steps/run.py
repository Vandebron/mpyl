"""
Accumulate `mpyl.steps.run.RunResult` from executed `mpyl.steps.step.Step`
"""

import operator
from typing import Optional

from .models import RunProperties
from ..project import Stage, Project
from .steps import StepResult


class RunResult:
    _run_plan: dict[Stage, set[Project]]
    _results: list[StepResult] = []
    _run_properties: RunProperties
    _exception: Optional[Exception]

    def __init__(self, run_properties: RunProperties, run_plan=None):
        if run_plan is None:
            run_plan = {}
        self._run_properties = run_properties
        self._run_plan = run_plan
        self._exception = None

    @property
    def status_line(self) -> str:
        if self._exception:
            return '❗ Failed with exception'
        if self.is_in_progress:
            return '🏗️ Building'
        if self._results_success():
            return '✅ Successful'

        return '❌ Failed'

    @property
    def progress_fraction(self) -> float:
        items = self.run_plan.items()

        total = sum(len(projects) for stage, projects in items)
        unfinished = 0
        for stage, projects in items:
            finished_project_names = set(map(lambda r: r.project.name, self.results_for_stage(stage)))
            for project in projects:
                if project.name not in finished_project_names:
                    unfinished += 1

        if unfinished == 0:
            return 1.0

        return 1.0 - (unfinished / total)

    @property
    def exception(self) -> Optional[Exception]:
        return self._exception

    @exception.setter
    def exception(self, exception: Exception):
        self._exception = exception

    @property
    def run_properties(self) -> RunProperties:
        return self._run_properties

    @property
    def run_plan(self) -> dict[Stage, set[Project]]:
        return self._run_plan

    def append(self, result: StepResult):
        self._results.append(result)

    def extend(self, results: list[StepResult]):
        self._results.extend(results)

    @property
    def is_success(self):
        if self._exception:
            return False
        return self._results_success()

    @property
    def is_finished(self):
        return self.progress_fraction == 1.0

    @property
    def is_in_progress(self):
        return self.is_success and not self.is_finished

    def _results_success(self):
        return all(r.output.success for r in self._results)

    @staticmethod
    def sort_chronologically(results: list[StepResult]) -> list[StepResult]:
        return sorted(results, key=operator.attrgetter('timestamp'))

    def results_for_stage(self, stage: Stage) -> list[StepResult]:
        return RunResult.sort_chronologically([res for res in self._results if res.stage == stage])

    def plan_for_stage(self, stage: Stage) -> set[Project]:
        plan: Optional[set[Project]] = self.run_plan.get(stage)
        if plan:
            return plan

        return set()
