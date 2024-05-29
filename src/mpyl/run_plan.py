"""This module contains the RunPlan class."""

from dataclasses import dataclass

from .project import Project, Stage
from .project_execution import ProjectExecution


@dataclass(frozen=True)
class RunPlan:
    full_plan: dict[Stage, set[ProjectExecution]]
    selected_plan: dict[Stage, set[ProjectExecution]]

    @classmethod
    def empty(cls) -> "RunPlan":
        return cls(full_plan={}, selected_plan={})

    @classmethod
    def from_plan(cls, plan: dict[Stage, set[ProjectExecution]]) -> "RunPlan":
        return cls(full_plan=plan, selected_plan=plan)

    def select_stage(self, stage: Stage) -> "RunPlan":
        return RunPlan(
            full_plan=self.full_plan,
            selected_plan={stage: self.get_projects_for_stage(stage)},
        )

    def select_projects(self, projects: set[Project]) -> "RunPlan":
        selected_plan = {}

        for stage, executions in self.selected_plan.items():
            selected_plan[stage] = {e for e in executions if e.project in projects}

        return RunPlan(
            full_plan=self.full_plan,
            selected_plan=selected_plan,
        )

    def update(self, run_plan: "RunPlan"):
        self.full_plan.update(run_plan.full_plan)
        self.selected_plan.update(run_plan.selected_plan)

    def has_projects_to_run(
        self, include_cached_projects: bool, use_full_plan: bool = False
    ) -> bool:
        return any(
            include_cached_projects or not project_execution.cached
            for project_execution in self.get_all_projects(use_full_plan)
        )

    def get_all_projects(self, use_full_plan: bool = False) -> set[ProjectExecution]:
        def flatten(plan: dict[Stage, set[ProjectExecution]]):
            return {
                project_execution
                for project_executions in plan.values()
                for project_execution in project_executions
            }

        if use_full_plan:
            return flatten(self.full_plan)
        return flatten(self.selected_plan)

    def get_projects_for_stage(
        self, stage: Stage, use_full_plan: bool = False
    ) -> set[ProjectExecution]:
        if use_full_plan:
            return self.full_plan.get(stage, set())
        return self.selected_plan.get(stage, set())

    def get_projects_for_stage_name(
        self, stage_name: str, use_full_plan: bool = False
    ) -> set[ProjectExecution]:
        def find_stage(plan: dict[Stage, set[ProjectExecution]]):
            iterator = (
                project_executions
                for stage, project_executions in plan.items()
                if stage.name == stage_name
            )
            return next(iterator, set())

        if use_full_plan:
            return find_stage(self.full_plan)
        return find_stage(self.selected_plan)
