import unittest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
import requests
from src.mpyl.steps.deploy.bpm.modeler import (
    File,
    get_file_data,
    update_diagram,
    create_milestone,
)
from src.mpyl.steps.deploy.bpm.camunda_modeler_client import CamundaModelerClient


class TestModeler(unittest.TestCase):
    @patch("requests.Session")
    @patch("requests.post")
    def test_get_files_succeed(self, mock_post, mock_session):
        excepted_data = {
            "items": [
                {
                    "id": "camundaUUID",
                    "name": "example process",
                    "projectId": "example_id",
                    "revision": 2,
                }
            ],
            "total": 1,
        }
        self.setup_mock_data(mock_post, mock_session, excepted_data)

        client = CamundaModelerClient(
            "https://modeler.test.camunda.io/api/v1/",
            "https://test.com/oauth/token",
            {},
        )

        result = get_file_data("example-process.bpmn", "example_id", client)
        assert result.file_id == "camundaUUID"
        assert result.revision == 2

        mock_session.return_value.request.assert_called_once_with(
            "POST",
            "https://modeler.test.camunda.io/api/v1/files/search",
            json={
                "filter": {
                    "name": "example process",
                    "projectId": "example_id",
                },
                "size": 10,
            },
            headers={"Authorization": "Bearer eyJhbG..."},
            params=None,
            data=None,
        )

    @patch("requests.Session")
    @patch("requests.post")
    def test_get_files_error_no_file_found(self, mock_post, mock_session):
        excepted_data = {"items": [], "total": 0}
        self.setup_mock_data(mock_post, mock_session, excepted_data)

        client = CamundaModelerClient(
            "https://modeler.test.camunda.io/api/v1/",
            "https://test.com/oauth/token",
            {},
        )

        with self.assertRaises(ValueError) as err:
            get_file_data("example-process.bpmn", "example_id", client)
        assert "no process called example process is found" in str(err.exception)

    @patch("requests.Session")
    @patch("requests.post")
    @patch(
        "src.mpyl.steps.deploy.bpm.modeler.open",
        mock_open(read_data="mock data"),
        create=True,
    )
    def test_update_diagram_succeed(self, mock_post, mock_session):
        self.setup_mock_data(mock_post, mock_session, {})

        client = CamundaModelerClient(
            "https://modeler.test.camunda.io/api/v1/",
            "https://test.com/oauth/token",
            {},
        )

        update_diagram("/resources", File("example process", "camundaUUID", 2), client)

        mock_session.return_value.request.assert_called_once_with(
            "PATCH",
            "https://modeler.test.camunda.io/api/v1/files/camundaUUID",
            json={"name": "example process", "content": "mock data", "revision": 2},
            headers={"Authorization": "Bearer eyJhbG..."},
            params=None,
            data=None,
        )

    @patch("requests.Session")
    @patch("requests.post")
    @patch("src.mpyl.steps.deploy.bpm.modeler.datetime")
    def test_create_milestone_succeed(self, mock_dt, mock_post, mock_session):
        fixed_time = datetime(2024, 5, 5, 10, 10, 12)
        mock_dt.now.return_value = fixed_time

        self.setup_mock_data(mock_post, mock_session, {})

        client = CamundaModelerClient(
            "https://modeler.test.camunda.io/api/v1/",
            "https://test.com/oauth/token",
            {},
        )

        create_milestone(File("example process", "camundaUUID", 2), "123", client)

        mock_session.return_value.request.assert_called_once_with(
            "POST",
            "https://modeler.test.camunda.io/api/v1/milestones",
            params=None,
            data=None,
            json={"name": "202405051010-123", "fileId": "camundaUUID"},
            headers={"Authorization": "Bearer eyJhbG..."},
        )

    def setup_mock_data(self, mock_post, mock_session, expected_data) -> None:
        token = Mock()
        token.return_value.status_code = 201
        token.json.return_value = {
            "access_token": "eyJhbG...",
            "expires_in": 300,
            "refresh_expires_in": 0,
            "token_type": "Bearer",
            "not-before-policy": 0,
        }
        mock_post.return_value = token

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_session.return_value.request.return_value = mock_response
