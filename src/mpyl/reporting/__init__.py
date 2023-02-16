from abc import abstractmethod

from ..steps.run import RunResult


class Reporter:

    @abstractmethod
    def send_report(self, results: RunResult) -> None:
        pass
