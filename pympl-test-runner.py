from dataclasses import dataclass

import yaml
from dagster import job, op, DynamicOut, DynamicOutput, get_dagster_logger

from src.pympl.project import load_project, Project
from src.pympl.repo import Repository, RepoConfig
from src.pympl.stage import Stage
from src.pympl.steps.models import BuildProperties, VersioningProperties, Output
from src.pympl.steps.steps import Steps
from src.pympl.target import Target


@dataclass
class StepParam:
    stage: Stage
    project: Project


def execute_step(param: Project, stage: Stage) -> Output:
    proj = param
    executor = Steps(get_dagster_logger())
    build_props = BuildProperties("1", Target.PULL_REQUEST, VersioningProperties("sha", "1234", None))
    return executor.execute(stage, proj, build_props)


@op
def build_project(project: Project) -> Output:
    return execute_step(project, Stage.BUILD)


@op
def test_project(project: Project):
    return execute_step(project, Stage.TEST)


@op
def deploy_project(project: Project):
    return execute_step(project, Stage.DEPLOY)


@op
def deploy_projects(outputs: list[Output]):
    print(f"Deploying {outputs}")


@op(out=DynamicOut())
def find_projects() -> list[DynamicOutput[Project]]:
    with open("config.yml") as f:
        yaml_values = yaml.load(f, Loader=yaml.FullLoader)
        repo = Repository(RepoConfig(yaml_values))
        project_paths = repo.find_projects()
        projects = map(lambda p: load_project(".", p), project_paths)
        return list(map(lambda project: DynamicOutput(project, mapping_key=project.name), projects))


@job
def run_build():
    projects = find_projects()
    build_results = projects.map(build_project)
    projects.map(test_project)
    deploy_projects(build_results.collect())