import logging
from dataclasses import dataclass
from logging import Logger

import yaml
from prefect import flow, task
from rich.console import Console
from rich.logging import RichHandler

from src.pympl.project import load_project, Project
from src.pympl.repo import Repository, RepoConfig, History
from src.pympl.stage import Stage
from src.pympl.steps.models import BuildProperties, VersioningProperties, Output
from src.pympl.steps.steps import Steps
from src.pympl.target import Target


@dataclass
class StepParam:
    stage: Stage
    project: Project


def main(repo: Repository, log: Logger):
    log.setLevel(logging.INFO)
    changes_in_branch: list[History] = repo.changes_in_branch()
    project_paths = repo.find_projects()

    all_projects = list(map(lambda p: load_project(".", p, False), project_paths))
    executor = Steps(logger=log)
    log.info(" Building projects")
    build_props = BuildProperties("1", Target.PULL_REQUEST, VersioningProperties(repo.get_sha, "1234", None))

    @task(name="Execute step", log_prints=True)
    def execute_step(param: StepParam) -> Output:
        proj = param.project
        print(f"Running {param.stage} for {proj.name}")
        return executor.execute(param.stage, proj, build_props)

    @flow(name="Build stage", log_prints=True)
    def build_projects(projects: set[str]):
        for proj in projects:
            print(f"Executing {proj}")
            output: Output = execute_step(StepParam(stage=Stage.BUILD, project=(load_project(".", proj))))
            print(f"Project {proj} success: {output.success}, message: {output.message}")

    @flow(name="Test stage", log_prints=True)
    def test_projects(projects: set[str]):
        for proj in projects:
            print(f"Executing {proj}")
            output: Output = execute_step(StepParam(stage=Stage.TEST, project=(load_project(".", proj))))
            print(f"Project {proj} success: {output.success}, message: {output.message}")

    @flow(name="CICD flow", log_prints=True)
    def run_build():
        build_projects(project_paths)
        test_projects(project_paths)

    run_build()


if __name__ == "__main__":
    FORMAT = "%(name)s  %(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True, console=Console(width=255), show_path=True)]
    )

    with open("config.yml") as f:
        yaml_values = yaml.load(f, Loader=yaml.FullLoader)
        main(Repository(RepoConfig(yaml_values)), logging.getLogger("mpl"))
