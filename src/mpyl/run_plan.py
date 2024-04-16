"""This module contains the RunPlan class."""

from dataclasses import dataclass

from .project import Stage
from .project_execution import ProjectExecution


@dataclass(frozen=True)
class RunPlan:
    plan: dict[Stage, set[ProjectExecution]]

    @staticmethod
    def empty() -> "RunPlan":
        return RunPlan({})

    def get(self, stage: Stage) -> set[ProjectExecution]:
        return self.plan.get(stage, set())

    def add_stage(self, stage: Stage, executions: set[ProjectExecution]):
        self.plan.update({stage: executions})

    def update(self, run_plan: "RunPlan"):
        self.plan.update(run_plan.plan)

    def items(self):
        return self.plan.items()
