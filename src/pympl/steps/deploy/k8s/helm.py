import subprocess
from logging import Logger
from pathlib import Path

from ....project import Project

chart = """
apiVersion: v2
name: service
description: A helm chart used by the MPL pipeline
type: application
version: 0.1.0
appVersion: "PR-123"
"""


def custom_check_output(command: str):
    output = subprocess.run(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if output.returncode == 0:
        return output.stdout.decode()

    return output.stderr.decode()


def install(logger: Logger, project: Project, name_space: str, chart_path: Path, templates: dict[str, str]) -> str:
    Path(chart_path).mkdir(parents=True, exist_ok=True)

    with open(chart_path / "Chart.yaml", mode='w+') as file:
        file.write(chart)
    with open(chart_path / "values.yaml", mode='w+') as file:
        file.write("")

    for k, v in templates.items():
        with open(chart_path / "templates" / str(k), mode='w+') as file:
            file.write(v)
    command = f"helm upgrade -i {project.name.lower()} -n {name_space} {chart_path}"
    logger.info(command)
    return custom_check_output(command)
