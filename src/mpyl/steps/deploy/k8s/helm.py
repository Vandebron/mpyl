""" This module is called on to create a helm chart for your project and install it during the `mpyl.steps.deploy`
step.
"""

import shutil
from dataclasses import dataclass
from io import StringIO
from logging import Logger
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from .resources import to_yaml, CustomResourceDefinition
from ...models import RunProperties, Output, Input
from ....utilities.subprocess import custom_check_output


@dataclass(frozen=True)
class ExternalHelmArguments:
    chart_name: str
    repo: str
    version: str


def to_chart_metadata(chart_name: str, run_properties: RunProperties):
    return f"""apiVersion: v3
name: {chart_name}
description: A helm chart used by the MPyL pipeline
type: application
version: 0.1.0
appVersion: "{run_properties.versioning.identifier}"
"""


def write_chart(chart: dict[str, CustomResourceDefinition], chart_path: Path, chart_metadata: str,
                values: Optional[str] = None) -> None:
    shutil.rmtree(chart_path, ignore_errors=True)
    template_path = chart_path / Path("templates")
    template_path.mkdir(parents=True, exist_ok=True)

    with open(chart_path / Path("Chart.yaml"), mode='w+', encoding='utf-8') as file:
        file.write(chart_metadata)
    with open(chart_path / Path("values.yaml"), mode='w+', encoding='utf-8') as file:
        if values is None:
            file.write("# This file is intentionally left empty. All values in /templates have been pre-interpolated")
        else:
            file.write(values)

    my_dictionary: dict[str, str] = dict(map(lambda item: (item[0], to_yaml(item[1])), chart.items()))

    for name, template in my_dictionary.items():
        with open(template_path / name, mode='w+', encoding='utf-8') as file:
            file.write(template)


def install(logger: Logger, chart: dict[str, CustomResourceDefinition], step_input: Input, chart_name: str,
            name_space: str, kube_context: str) -> Output:
    chart_path = Path(step_input.project.target_path) / "chart"
    write_chart(chart, chart_path, to_chart_metadata(chart_name, step_input.run_properties))

    effective_name_space = 'namespace' if step_input.dry_run else name_space
    cmd = f"helm upgrade -i {chart_name} -n {effective_name_space} --kube-context {kube_context} {chart_path}"
    if step_input.dry_run:
        cmd += " --debug --dry-run"

    return custom_check_output(logger, cmd)


def install_external(logger: Logger, values: dict, step_input: Input, release_name: str,
                     name_space: str, kube_context: str, helm_args: ExternalHelmArguments) -> Output:
    chart_path = Path(step_input.project.target_path) / "chart"
    values_path = chart_path / "values.yaml"
    stream = StringIO()
    YAML().dump(values, stream)

    write_chart(chart={}, chart_path=chart_path,
                chart_metadata=to_chart_metadata(release_name, step_input.run_properties), values=stream.getvalue())

    effective_name_space = 'namespace' if step_input.dry_run else name_space

    cmd = f"helm upgrade {helm_args.chart_name} {release_name} -i -n {effective_name_space} " \
          f"--kube-context {kube_context} --values {values_path} --repo {helm_args.repo} --version {helm_args.version}"
    if step_input.dry_run:
        cmd += " --debug --dry-run"

    return custom_check_output(logger, cmd)
