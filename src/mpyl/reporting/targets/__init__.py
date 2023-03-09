"""
Interface for custom reporters.
To create a new reporter, implement `Reporter.send_report`.
You can transform `mpyl.steps.run.RunResult` to a report using any of the standard formatters under
`mpyl.reporting.formatting` and send it to target of your choice.

See the **Submodules** for built-in reporters.
"""
from abc import abstractmethod

from ...steps.run import RunResult


class Reporter:

    @abstractmethod
    def send_report(self, results: RunResult) -> None:
        pass
