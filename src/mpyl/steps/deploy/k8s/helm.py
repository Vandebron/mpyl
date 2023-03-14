""" This module is called on to create a helm chart for your project and install it during the `mpyl.steps.deploy`
step.
"""

import shutil
from logging import Logger
from pathlib import Path

from .chart import ChartBuilder, to_service_chart
from .resources.crd import to_yaml
from ...models import RunProperties, Input, Output
from ....utilities.subprocess import custom_check_output


def to_chart_metadata(chart_name: str, run_properties: RunProperties):
    return f"""apiVersion: v3
name: {chart_name}
description: A helm chart used by the MPL pipeline
type: application
version: 0.1.0
appVersion: "{run_properties.versioning.identifier}"
"""


def write_chart(step_input: Input, chart_path: Path, chart_metadata: str) -> None:
    builder = ChartBuilder(step_input)

    shutil.rmtree(chart_path, ignore_errors=True)
    template_path = chart_path / Path("templates")
    template_path.mkdir(parents=True, exist_ok=True)

    with open(chart_path / Path("Chart.yaml"), mode='w+', encoding='utf-8') as file:
        file.write(chart_metadata)
    with open(chart_path / Path("values.yaml"), mode='w+', encoding='utf-8') as file:
        file.write("# This file is intentionally left empty. All values in /templates have been pre-interpolated")

    templates = to_service_chart(builder)
    my_dictionary: dict[str, str] = dict(map(lambda item: (item[0], to_yaml(item[1])), templates.items()))

    for name, template in my_dictionary.items():
        with open(template_path / name, mode='w+', encoding='utf-8') as file:
            file.write(template)


def install(logger: Logger, step_input: Input, name_space: str, kube_context: str) -> Output:
    chart_name = step_input.project.name.lower()
    chart_path = Path(step_input.project.target_path) / "chart"
    write_chart(step_input, chart_path, to_chart_metadata(chart_name, step_input.run_properties))

    cmd = f"helm upgrade -i {chart_name} -n {name_space} --kube-context {kube_context} {chart_path}"
    if step_input.dry_run:
        cmd = f"helm upgrade -i {chart_name} -n namespace --kube-context {kube_context} {chart_path} --debug --dry-run"

    return custom_check_output(logger, cmd)
