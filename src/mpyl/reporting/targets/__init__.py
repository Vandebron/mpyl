"""
Interface for custom reporters.
To create a new reporter, implement `Reporter.send_report`.
You can transform `mpyl.steps.run.RunResult` to a report using any of the standard formatters under
`mpyl.reporting.formatting` and send it to target of your choice.

See the **Submodules** for built-in reporters.
"""
from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from ...steps.run import RunResult


@dataclass(frozen=True)
class ReportOutcome:
    success: bool
    exception: Optional[Exception] = None


class ReportAccumulator:
    outcomes: list[ReportOutcome]

    def __init__(self):
        self.outcomes = []

    def add(self, outcome: ReportOutcome):
        self.outcomes.append(outcome)

    @property
    def failures(self) -> list[str]:
        return [
            f"{type(outcome).__name__} failed with exception {outcome.exception}"
            for outcome in self.outcomes
            if not outcome.success
        ]


class Reporter:
    @abstractmethod
    def send_report(
        self, results: RunResult, text: Optional[str] = None
    ) -> ReportOutcome:
        pass
