import logging

from src.pympl.project import load_project
from src.pympl.repo import Repository
from src.pympl.stage import Stage
from src.pympl.stages.discovery import find_invalidated_projects_for_stage
from src.pympl.steps.steps import Steps

import logging
from rich.logging import RichHandler
from rich.console import Console


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True, console=Console(width=255), show_path=True)]
    )

    loggert = logging.getLogger("mpl")
    loggert.info("Hello, World!")
    repo = Repository('main')
    changes_in_branch = repo.changes_in_branch()
    changes_in_commit = repo.changes_in_commit()
    loggert.info(f" In branch\n {changes_in_branch}")
    loggert.info(f" In commit\n {changes_in_commit}")

    project_paths = repo.find_projects()
    logging.info(f" Projects: {len(project_paths)}")
    # for path in project_paths:
    #     print("loading: ", path)
    #     load_project('../..', path, False)

    loggert.info(f" Build stage: {len(find_invalidated_projects_for_stage(repo, Stage.BUILD, changes_in_branch))}")
    loggert.info(f" Test stage: {len(find_invalidated_projects_for_stage(repo, Stage.TEST, changes_in_branch))}")
    loggert.info(f" Deploy stage: {len(find_invalidated_projects_for_stage(repo, Stage.DEPLOY, changes_in_branch))}")
    loggert.info(f" Post deploy stage: {len(find_invalidated_projects_for_stage(repo, Stage.POST_DEPLOY, changes_in_branch))}")

    all_projects = list(map(lambda p: load_project(".", p, False), project_paths))
    executor = Steps(logger=loggert)

    loggert.info(" Building projects")
    for proj in all_projects:
        executor.execute(Stage.BUILD, proj)

    for proj in all_projects:
        executor.execute(Stage.DEPLOY, proj)
    # executor.execute()
