"""This module contains the RunPlan class."""

from dataclasses import dataclass

from .project import Project, Stage
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

    def for_stage(self, stage: Stage) -> "RunPlan":
        return RunPlan({stage: self.get(stage)})

    def for_projects(self, projects: set[Project]):
        return RunPlan(
            {
                stage: {e for e in executions if e.project in projects}
                for stage, executions in self.plan.items()
            }
        )
