"""Camunda modeler related methods to deploy diagrams"""

import os
from collections import namedtuple
from datetime import datetime
from logging import Logger

from .camunda_modeler_client import CamundaModelerClient
from ....project import Target
from ....utilities.bpm import CamundaConfig

File = namedtuple("File", ["name", "file_id", "revision"])


def deploy_diagram_to_modeler(
    logger: Logger,
    bpm_file_path: str,
    config: CamundaConfig,
    client: CamundaModelerClient,
    pr_number: str,
) -> None:
    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        logger.info(f"Updating diagram: {file_name}")
        file_info = get_file_data(file_name, config.project_id, client)
        file_path = os.path.join(bpm_file_path, file_name)
        update_diagram(file_path, file_info, client)
        if config.target == Target.PULL_REQUEST_BASE:
            create_milestone(file_info, pr_number, client)


def get_file_data(
    file_name: str, project_id: str, client: CamundaModelerClient
) -> File:
    search_name = file_name.replace("-", " ").rstrip(".bpmn")
    request = {
        "filter": {
            "name": search_name,
            "projectId": project_id,
        },
        "size": 10,
    }
    res = client.get_files(request)
    if len(res.get("items")) == 1:
        file = File(
            res.get("items")[0].get("name"),
            res.get("items")[0].get("id"),
            res.get("items")[0].get("revision"),
        )
        return file
    raise ValueError(f"no process called {search_name} is found")


def update_diagram(
    file_path: str, file_data: File, client: CamundaModelerClient
) -> None:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    if content is not None:
        request = {
            "name": file_data.name,
            "content": content,
            "revision": file_data.revision,
        }
        client.update_file_in_modeler(file_data.file_id, request)


def create_milestone(
    file_data: File, pr_number: str, client: CamundaModelerClient
) -> None:
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%Y%m%d%H%M")
    milestone_name = formatted_date_time + "-" + pr_number
    request = {
        "name": milestone_name,
        "fileId": file_data.file_id,
    }

    client.create_milestone_in_modeler(request)
