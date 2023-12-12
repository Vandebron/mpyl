"""Module to initiate run properties"""
import logging
from pathlib import Path
from typing import Optional

from ..cli import MpylCliParameters
from ..project import load_project, Stage, Project
from ..stages.discovery import find_build_set
from ..steps.models import RunProperties
from ..utilities.repo import Repository, RepoConfig


def initiate_run_properties(
    config: dict,
    properties: dict,
    cli_parameters: MpylCliParameters = MpylCliParameters(),
    run_plan: Optional[dict[Stage, set[Project]]] = None,
    all_projects: Optional[set[Project]] = None,
) -> RunProperties:
    tag = cli_parameters.tag or properties["build"]["versioning"].get("tag")
    if all_projects is None or run_plan is None:
        with Repository(RepoConfig.from_config(config)) as repo:
            if all_projects is None:
                project_paths = repo.find_projects()
                all_projects = set(
                    map(
                        lambda p: load_project(
                            root_dir=Path(""),
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
                run_plan = find_build_set(
                    logger=logging.getLogger("mpyl"),
                    all_projects=all_projects,
                    changes_in_branch=(
                        repo.changes_in_branch_including_local()
                        if cli_parameters.local
                        else (
                            repo.changes_in_tagged_commit(tag)
                            if tag
                            else repo.changes_in_branch()
                        )
                    ),
                    stages=stages,
                    build_all=cli_parameters.all,
                    selected_stage=cli_parameters.stage,
                    selected_projects=cli_parameters.projects,
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
