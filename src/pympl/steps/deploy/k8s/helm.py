import shutil
import subprocess
from logging import Logger
from pathlib import Path

from .service import ServiceChart
from ...models import BuildProperties, Input


def custom_check_output(command: str):
    output = subprocess.run(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if output.returncode == 0:
        return output.stdout.decode()

    return output.stderr.decode()


def to_chart(chart_name: str, build_properties: BuildProperties):
    return f"""apiVersion: v3
name: {chart_name}
description: A helm chart used by the MPL pipeline
type: application
version: 0.1.0
appVersion: "{build_properties.versioning.identifier}"
"""


def install(logger: Logger, step_input: Input, name_space: str) -> str:
    if step_input.required_artifact:
        image_name = step_input.required_artifact.spec['image']
    else:
        raise ValueError('Required artifact must be defined')
    service_chart = ServiceChart(step_input, image_name)

    templates = service_chart.to_chart()

    chart_path = Path(step_input.project.target_path) / "chart"

    shutil.rmtree(chart_path, ignore_errors=True)
    template_path = chart_path / "templates"
    Path(template_path).mkdir(parents=True, exist_ok=True)

    chart_name = step_input.project.name.lower()

    chart = to_chart(chart_name, step_input.build_properties)

    with open(chart_path / "Chart.yaml", mode='w+', encoding='utf-8') as file:
        file.write(chart)
    with open(chart_path / "values.yaml", mode='w+', encoding='utf-8') as file:
        file.write("# This file is intentionally left empty. All values in /templates have been pre-interpolated")

    for name, template in templates.items():
        with open(template_path / str(name), mode='w+', encoding='utf-8') as file:
            file.write(template)
    command = f"helm upgrade -i {chart_name} -n {name_space} {chart_path}"
    logger.info(command)
    return custom_check_output(command)
