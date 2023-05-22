""" This module is called on to create a helm chart for your project and install it during the `mpyl.steps.deploy`
step.
"""

import shutil
from logging import Logger
from pathlib import Path

from .resources import to_yaml, CustomResourceDefinition
from ...models import RunProperties, Output, Input
from ....utilities.subprocess import custom_check_output


def to_chart_metadata(chart_name: str, run_properties: RunProperties):
    return f"""apiVersion: v3
name: {chart_name}
description: A helm chart used by the MPyL pipeline
type: application
version: 0.1.0
appVersion: "{run_properties.versioning.identifier}"
"""


def write_chart(chart: dict[str, CustomResourceDefinition], chart_path: Path, chart_metadata: str) -> None:
    shutil.rmtree(chart_path, ignore_errors=True)
    template_path = chart_path / Path("templates")
    template_path.mkdir(parents=True, exist_ok=True)

    with open(chart_path / Path("Chart.yaml"), mode='w+', encoding='utf-8') as file:
        file.write(chart_metadata)
    with open(chart_path / Path("values.yaml"), mode='w+', encoding='utf-8') as file:
        file.write("# This file is intentionally left empty. All values in /templates have been pre-interpolated")

    my_dictionary: dict[str, str] = dict(map(lambda item: (item[0], to_yaml(item[1])), chart.items()))

    for name, template in my_dictionary.items():
        with open(template_path / name, mode='w+', encoding='utf-8') as file:
            file.write(template)


def __remove_existing_chart(logger: Logger, chart_name: str, name_space: str, kube_context: str) -> Output:
    found_chart = custom_check_output(logger, f"helm list -f ^{chart_name}$ -n {name_space}", capture_stdout=True)
    if chart_name in found_chart.message:
        cmd = f"helm uninstall {chart_name} -n {name_space} --kube-context {kube_context}"
        return custom_check_output(Logger("helm"), cmd)
    return Output(success=True, message=f"No existing chart {chart_name} found to delete")


def install(logger: Logger, chart: dict[str, CustomResourceDefinition], step_input: Input, chart_name: str,
            name_space: str, kube_context: str, delete_existing: bool = False) -> Output:
    if delete_existing:
        removed = __remove_existing_chart(logger, chart_name, name_space, kube_context)
        if not removed.success:
            return removed

    chart_path = Path(step_input.project.target_path) / "chart"
    logger.info(f"Writing HELM chart to {chart_path}")
    write_chart(chart, chart_path, to_chart_metadata(chart_name, step_input.run_properties))

    cmd = f"helm upgrade -i {chart_name} -n {name_space} --kube-context {kube_context} {chart_path}"
    if step_input.dry_run:
        cmd = f"helm upgrade -i {chart_name} -n namespace --kube-context {kube_context} {chart_path} --debug --dry-run"

    return custom_check_output(logger, cmd)
