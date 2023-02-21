import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from dagster import job, op, In, Nothing, DynamicOut, DynamicOutput, get_dagster_logger, Output, Failure, logger, Field
from pyaml_env import parse_config
from rich.logging import RichHandler, Console
from rich.text import Text

from src.mpyl.project import load_project, Project, Stage
from src.mpyl.repo import Repository, RepoConfig
from src.mpyl.reporting.simple import to_string
from src.mpyl.reporting.targets.github import GithubReport
from src.mpyl.steps.models import RunProperties
from src.mpyl.steps.run import RunResult
from src.mpyl.steps.steps import Steps, StepResult


@dataclass
class StepParam:
    stage: Stage
    project: Project


def execute_step(proj: Project, stage: Stage, dry_run: bool = False) -> StepResult:
    config = parse_config("config.yml")
    properties = parse_config("run_properties.yml")
    run_properties = RunProperties.from_configuration(run_properties=properties, config=config)
    dagster_logger = get_dagster_logger()
    executor = Steps(dagster_logger, run_properties)
    step_result = executor.execute(stage, proj, dry_run)
    if not step_result.output.success:
        raise Failure(description=step_result.output.message)
    return step_result


@op(description="Build stage. Build steps produce a docker image", config_schema={"dry_run": bool})
def build_project(context, project: Project) -> Output:
    dry_run: bool = context.op_config["dry_run"]
    return Output(execute_step(project, Stage.BUILD, dry_run))


@op
def test_project(context, projects: list[Project], _ignored: Output) -> Output:
    for project in projects:
        return Output(execute_step(project, Stage.TEST))


@op(description="Deploy a project to the target specified in the step", config_schema={"dry_run": bool})
def deploy_project(context, project: Project) -> Output:
    dry_run: bool = context.op_config["dry_run"]
    return Output(execute_step(project, Stage.DEPLOY, dry_run))


@op(description="Deploy all artifacts produced over all runs of the pipeline")
def deploy_projects(context, projects: list[Project], outputs: list[StepResult]) -> Output[list[StepResult]]:
    dry_run: bool = context.op_config["dry_run"]
    res = []
    for proj in projects:
        res.append(execute_step(proj, Stage.DEPLOY, dry_run))
    return Output(res)


@op(description="Log run results and send to Github")
def report_results(build_results: list[StepResult], deploy_results: list[StepResult]) -> bool:
    config = parse_config("config.yml")

    properties = RunProperties.from_configuration(parse_config("run_properties.yml"), config)

    run_result = RunResult(properties)
    run_result.extend(build_results)
    run_result.extend(deploy_results)

    get_dagster_logger().info(to_string(run_result))

    report = GithubReport(config)
    report.send_report(run_result)
    return True


@op(out=DynamicOut(), description="Find artifacts that need to be built")
def find_projects() -> list[DynamicOutput[Project]]:
    yaml_values = parse_config("config.yml")
    repo = Repository(RepoConfig(yaml_values))
    project_paths = repo.find_projects()
    projects = map(lambda p: load_project(".", p), project_paths)
    return list(map(lambda project: DynamicOutput(project, mapping_key=project.name), projects))


class CustomRichHandler(RichHandler):

    @staticmethod
    def format_datetime(timestamp: datetime) -> Text:
        return Text.from_markup(timestamp.strftime("%y-%m-%d %H:%M:%S"))

    def __init__(
            self,
            level: Union[int, str] = logging.NOTSET

    ) -> None:
        super().__init__(level=level, show_path=True, console=Console(width=135, no_color=False, color_system='256'),
                         log_time_format=CustomRichHandler.format_datetime)
        self._log_render.level_width = 4

    def emit(self, record: logging.LogRecord) -> None:
        meta = getattr(record, 'dagster_meta', None)
        if meta:
            record.pathname = meta['step_key']
            record.lineno = None
        super().emit(record)

    def render_message(self, record: logging.LogRecord, message: str) -> "ConsoleRenderable":
        use_markup = getattr(record, "markup", self.markup)
        message_text = Text.from_markup(message) if use_markup else Text.from_ansi(message)

        highlighter = getattr(record, "highlighter", self.highlighter)
        if highlighter:
            message_text = highlighter(message_text)

        if self.keywords is None:
            self.keywords = self.KEYWORDS

        if self.keywords:
            message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text


@logger(
    {
        "log_level": Field(str, is_required=False, default_value="INFO"),
        "name": Field(str, is_required=False, default_value="dagster"),
    },
    description="A Rich logger that includes the step context",
)
def mpyl_logger(init_context):
    level = init_context.logger_config["log_level"]
    name = init_context.logger_config["name"]

    klass = logging.getLoggerClass()
    logger_ = klass(name, level=level)

    rich_handler = CustomRichHandler()

    class DagsterFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord):
            meta = getattr(record, 'dagster_meta', None)
            if meta:
                return meta['orig_message']

            return record.msg

    rich_handler.setFormatter(DagsterFormatter())
    logger_.addHandler(rich_handler)

    return logger_


@job(logger_defs={"mpyl_logger": mpyl_logger})
def run_build():
    projects = find_projects()
    build_results = projects.map(build_project)
    test_project(
        projects.collect(),
        build_results.collect()
    )
    deploy_results = deploy_projects(
        projects=projects.collect(),
        outputs=build_results.collect()
    )
    report_results(build_results=build_results.collect(), deploy_results=deploy_results)


if __name__ == "__main__":
    result = run_build.execute_in_process(run_config={
        'loggers': {'mpyl_logger': {'config': {'log_level': 'INFO'}}},
        'ops': {
            'build_project': {'config': {'dry_run': True}},
            'deploy_projects': {'config': {'dry_run': True}}
        }
    })
    print(f"Result: {result.success}")
