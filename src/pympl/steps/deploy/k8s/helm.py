import shutil
import subprocess
from logging import Logger
from pathlib import Path

from ....project import Project

# TODO: interpolate version info
CHART = """
apiVersion: v3
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
    shutil.rmtree(chart_path, ignore_errors=True)
    template_path = chart_path / "templates"
    Path(template_path).mkdir(parents=True, exist_ok=True)

    with open(chart_path / "Chart.yaml", mode='w+', encoding='utf-8') as file:
        file.write(CHART)
    with open(chart_path / "values.yaml", mode='w+', encoding='utf-8') as file:
        file.write("# This file is intentionally left empty. All values in /templates have been pre-interpolated")

    for k, v in templates.items():
        with open(template_path / str(k), mode='w+', encoding='utf-8') as file:
            file.write(v)
    command = f"helm upgrade -i {project.name.lower()} -n {name_space} {chart_path}"
    logger.info(command)
    return custom_check_output(command)
