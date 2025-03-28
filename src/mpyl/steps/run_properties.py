"""Module to initiate run properties"""

import logging
from pathlib import Path
from typing import Optional

from ..cli import MpylCliParameters
from ..project import load_project, Stage, Project
from ..run_plan import RunPlan
from ..stages.discovery import create_run_plan
from ..steps.models import RunProperties
from ..utilities.repo import Repository, RepoConfig


def construct_run_properties(
    config: dict,
    properties: dict,
    cli_parameters: MpylCliParameters = MpylCliParameters(),
    run_plan: Optional[RunPlan] = None,
    all_projects: Optional[set[Project]] = None,
    root_dir: Path = Path(""),
    explain_run_plan: bool = False,
) -> RunProperties:
    tag = cli_parameters.tag or properties["build"]["versioning"].get("tag")
    if all_projects is None or run_plan is None:
        with Repository(RepoConfig.from_config(config)) as repo:
            if all_projects is None:
                project_paths = repo.find_projects()
                all_projects = set(
                    map(
                        lambda p: load_project(
                            root_dir=root_dir,
                            project_path=Path(p),
                            strict=False,
                            log=True,
                            safe=True,
                        ),
                        project_paths,
                    )
                )

            if run_plan is None:
                stages = [
                    Stage(stage["name"], stage["icon"])
                    for stage in properties["stages"]
                ]
                run_plan_logger = logging.getLogger("mpyl")
                if explain_run_plan:
                    run_plan_logger.setLevel("DEBUG")
                changed_files_path = config["vcs"].get("changedFilesPath", None)
                run_plan = _create_run_plan(
                    cli_parameters=cli_parameters,
                    all_projects=all_projects,
                    all_stages=stages,
                    explain_run_plan=explain_run_plan,
                    repo=repo,
                    tag=tag,
                    changed_files_path=changed_files_path,
                )

    if cli_parameters.local:
        return RunProperties.for_local_run(
            config=config,
            run_plan=run_plan,
            revision=repo.get_sha,
            branch=repo.get_branch,
            tag=tag,
            stages=stages,
            all_projects=all_projects,
        )

    return RunProperties.from_configuration(
        run_properties=properties,
        config=config,
        run_plan=run_plan,
        all_projects=all_projects,
        cli_tag=tag,
    )


def _create_run_plan(
    cli_parameters: MpylCliParameters,
    all_projects: set[Project],
    all_stages: list[Stage],
    explain_run_plan: bool,
    repo: Repository,
    tag: Optional[str] = None,
    changed_files_path: Optional[str] = None,
):
    run_plan_logger = logging.getLogger("mpyl")
    if explain_run_plan:
        run_plan_logger.setLevel("DEBUG")

    if cli_parameters.stage:
        selected_stage = next(
            (stage for stage in all_stages if stage.name == cli_parameters.stage), None
        )
    else:
        selected_stage = None

    if cli_parameters.projects:
        selected_projects = {
            p for p in all_projects if p.name in cli_parameters.projects.split(",")
        }
    else:
        selected_projects = set()

    return create_run_plan(
        logger=run_plan_logger,
        repository=repo,
        all_projects=all_projects,
        all_stages=all_stages,
        tag=tag,
        local=cli_parameters.local,
        build_all=cli_parameters.all,
        selected_stage=selected_stage,
        selected_projects=selected_projects,
        changed_files_path=changed_files_path,
    )
