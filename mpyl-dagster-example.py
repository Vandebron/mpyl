from pathlib import Path

from dagster import (
    config_from_files,
    op,
    DynamicOut,
    DynamicOutput,
    get_dagster_logger,
    Output,
    Failure,
    job,
)

from mpyl.project import load_project, Project
from mpyl.stages.discovery import build_project_executions
from mpyl.steps import build, test, deploy
from mpyl.steps.run_properties import initiate_run_properties
from mpyl.steps.steps import Steps, StepResult
from mpyl.utilities.pyaml_env import parse_config
from mpyl.utilities.repo import Repository, RepoConfig

ROOT_PATH = "./"


def execute_step(proj: Project, stage: str, dry_run: bool = True) -> StepResult:
    config = parse_config(Path(f"{ROOT_PATH}mpyl_config.yml"))
    run_properties = initiate_run_properties(config=config, properties={}, run_plan={})
    dagster_logger = get_dagster_logger()
    executor = Steps(dagster_logger, run_properties)
    step_result = executor.execute(stage, proj, dry_run)
    if not step_result.output.success:
        raise Failure(description=step_result.output.message)
    return step_result


@op(description="Build stage. Build steps produce a docker image")
def build_project(context, project: Project) -> Output:
    return Output(execute_step(project, build.STAGE_NAME))


@op(description="Test stage. Test steps produce junit compatible test results")
def test_project(context, project) -> Output:
    return Output(execute_step(project, test.STAGE_NAME))


@op(
    description="Deploy a project to the target specified in the step",
    config_schema={"dry_run": bool},
)
def deploy_project(context, project: Project) -> Output:
    dry_run: bool = context.op_config["dry_run"]
    return Output(execute_step(project, deploy.STAGE_NAME, dry_run))


@op(
    description="Deploy all artifacts produced over all runs of the pipeline",
    config_schema={"simulate_deploy": bool},
)
def deploy_projects(
    context, projects: list[Project], outputs: list[StepResult]
) -> Output[list[StepResult]]:
    simulate_deploy: bool = context.op_config["simulate_deploy"]
    res = []
    if simulate_deploy:
        for proj in projects:
            res.append(execute_step(proj, deploy.STAGE_NAME))
    else:
        get_dagster_logger().info(f"Not deploying {projects}")
    return Output(res)


def find_projects(stage: str) -> list[DynamicOutput[Project]]:
    yaml_values = parse_config(Path(f"{ROOT_PATH}mpyl_config.yml"))
    with Repository(RepoConfig.from_config(yaml_values)) as repo:
        changes_in_branch = repo.changes_in_branch_including_local()
        project_paths = repo.find_projects()
    all_projects = set(
        map(lambda p: load_project(Path("."), Path(p), strict=False), project_paths)
    )
    invalidated = build_project_executions(all_projects, stage, changes_in_branch)
    return list(
        map(
            lambda project: DynamicOutput(
                project, mapping_key=project.name.replace("-", "_")
            ),
            invalidated,
        )
    )


@op(out=DynamicOut(), description="Find artifacts that need to be built")
def find_build_projects() -> list[DynamicOutput[Project]]:
    return find_projects(build.STAGE_NAME)


@op(out=DynamicOut(), description="Find artifacts that need to be tested")
def find_test_projects(_projects) -> list[DynamicOutput[Project]]:
    return find_projects(test.STAGE_NAME)


@op(out=DynamicOut(), description="Find artifacts that need to be deployed")
def find_deploy_projects(_projects) -> list[DynamicOutput[Project]]:
    return find_projects(deploy.STAGE_NAME)


@job(config=config_from_files(["mpyl-dagster-example.yml"]))
def run_build():
    build_projects = find_build_projects()
    build_results = build_projects.map(build_project)

    test_projects = find_test_projects(build_results.collect())
    test_results = test_projects.map(test_project)

    projects_to_deploy = find_deploy_projects(test_projects.collect())

    deploy_projects(
        projects=projects_to_deploy.collect(), outputs=test_results.collect()
    )
