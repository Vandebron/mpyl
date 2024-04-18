"""Camunda modeler related methods to deploy diagrams"""

import os
from logging import Logger
from collections import namedtuple
from .camunda_modeler_client import CamundaModelerClient

File = namedtuple("File", ["name", "file_id", "revision"])


def deploy_diagram_to_modeler(
    logger: Logger, bpm_file_path: str, project_id: str, client: CamundaModelerClient
) -> None:
    for file_name in (
        [fn for fn in os.listdir(bpm_file_path) if fn.endswith(".bpmn")]
        if os.path.isdir(bpm_file_path)
        else []
    ):
        logger.info(f"Updating diagram: {file_name}")
        file_info = get_file_data(file_name, project_id, client)
        file_path = os.path.join(bpm_file_path, file_name)
        update_diagram(file_path, file_info, client)


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
