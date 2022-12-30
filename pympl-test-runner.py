from dataclasses import dataclass

from dagster import job, op, DynamicOut, DynamicOutput, get_dagster_logger, Output, Failure
from pyaml_env import parse_config

from src.pympl.project import load_project, Project
from src.pympl.repo import Repository, RepoConfig
from src.pympl.stage import Stage
from src.pympl.steps.models import BuildProperties, VersioningProperties, Output as MplOutput
from src.pympl.steps.steps import Steps
from src.pympl.target import Target


@dataclass
class StepParam:
    stage: Stage
    project: Project


def execute_step(param: Project, stage: Stage) -> MplOutput:
    proj = param
    yaml_values = parse_config("config.yml")

    build_props = BuildProperties("1", Target.PULL_REQUEST, VersioningProperties("sha", "1234", None), yaml_values)
    executor = Steps(get_dagster_logger(), build_props)
    step_output = executor.execute(stage, proj)
    if not step_output.success:
        raise Failure(description=step_output.message)
    return step_output


@op
def build_project(project: Project) -> Output:
    return Output(execute_step(project, Stage.BUILD))


@op
def test_project(project: Project) -> Output:
    return Output(execute_step(project, Stage.TEST))


@op
def deploy_project(project: Project) -> Output:
    return Output(execute_step(project, Stage.DEPLOY))


@op(out=DynamicOut())
def deploy_projects(projects: list[Project], outputs: list[MplOutput]):
    for proj in projects:
        result = execute_step(proj, Stage.DEPLOY)
        yield DynamicOutput(result, mapping_key=f"deployed_{proj.name}")


@op(out=DynamicOut())
def find_projects() -> list[DynamicOutput[Project]]:
    yaml_values = parse_config("config.yml")
    repo = Repository(RepoConfig(yaml_values))
    project_paths = repo.find_projects()
    projects = map(lambda p: load_project(".", p), project_paths)
    return list(map(lambda project: DynamicOutput(project, mapping_key=project.name), projects))


@job
def run_build():
    projects = find_projects()
    build_results = projects.map(build_project)
    projects.map(test_project)
    deploy_projects(
        projects=projects.collect(),
        outputs=build_results.collect()
    )
