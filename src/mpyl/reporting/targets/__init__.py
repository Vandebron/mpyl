"""
Interface for custom reporters. Take `mpyl.steps.run.RunResult` and send it
to the report target of your choice.
"""
from abc import abstractmethod

from ...steps.run import RunResult


class Reporter:

    @abstractmethod
    def send_report(self, results: RunResult) -> None:
        pass
