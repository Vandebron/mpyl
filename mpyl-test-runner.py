from dataclasses import dataclass

from dagster import job, op, DynamicOut, DynamicOutput, get_dagster_logger, Output, Failure
from pyaml_env import parse_config

from src.mpyl.project import load_project, Project
from src.mpyl.repo import Repository, RepoConfig
from src.mpyl.stage import Stage
from src.mpyl.steps.models import BuildProperties, Output as MplOutput
from src.mpyl.steps.steps import Steps


@dataclass
class StepParam:
    stage: Stage
    project: Project


def execute_step(proj: Project, stage: Stage) -> MplOutput:
    config = parse_config("config.yml")
    properties = parse_config("build_properties.yml")
    build_props = BuildProperties.from_configuration(build_properties=properties, config=config)
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
