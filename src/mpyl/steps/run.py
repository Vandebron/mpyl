"""
Accumulate `mpyl.steps.run.RunResult` from executed `mpyl.steps.step.Step`
"""

import operator
from typing import Optional

from .models import RunProperties
from ..project import Stage
from .steps import StepResult


class RunResult:
    _results: list[StepResult] = []
    _run_properties: RunProperties
    _exception: Optional[Exception]

    def __init__(self, run_properties: RunProperties):
        self._run_properties = run_properties

    @property
    def run_properties(self) -> RunProperties:
        return self._run_properties

    def append(self, result: StepResult):
        self._results.append(result)

    def extend(self, results: list[StepResult]):
        self._results.extend(results)

    @property
    def is_success(self):
        return all(r.output.success for r in self._results)

    @staticmethod
    def sort_chronologically(results: list[StepResult]) -> list[StepResult]:
        return sorted(results, key=operator.attrgetter('timestamp'))

    def results_for_stage(self, stage: Stage) -> list[StepResult]:
        return RunResult.sort_chronologically([res for res in self._results if res.stage == stage])
