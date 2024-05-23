"""This module contains the RunPlan class."""
from dataclasses import dataclass
from typing import Optional

from .project import Project, Stage
from .project_execution import ProjectExecution


@dataclass()
class RunPlan:
    full_plan: dict[Stage, set[ProjectExecution]]
    _selected_stages: Optional[Stage] = None
    _selected_projects: Optional[set[Project]] = None
    _selected_plan: Optional[dict[Stage, set[ProjectExecution]]] = None

    @staticmethod
    def empty() -> "RunPlan":
        return RunPlan(full_plan={})

    @property
    def selected_stage(self) -> Optional[Stage]:
        return self._selected_stages

    @selected_stage.setter
    def selected_stage(self, stage: Stage):
        self._selected_stages = stage

    @property
    def selected_projects(self) -> Optional[set[Project]]:
        return self._selected_projects

    @selected_projects.setter
    def selected_projects(self, projects: set[Project]):
        self._selected_projects = projects

    @property
    def selected_plan(self) -> dict[Stage, set[ProjectExecution]]:
        if not self.selected_stage and not self._selected_projects:
            return self.full_plan

        self._selected_plan = {}
        for stage, executions in self.full_plan.items():
            if self.selected_stage and stage != self.selected_stage:
                continue

            self._selected_plan[stage] = executions

            if self.selected_projects:
                self._selected_plan[stage] = {
                    execution
                    for execution in executions
                    if execution.project in self.selected_projects
                }

        return self._selected_plan

    def add_stage(self, stage: Stage, executions: set[ProjectExecution]):
        self.full_plan.update({stage: executions})

    def update(self, run_plan: "RunPlan"):
        self.full_plan.update(run_plan.full_plan)
