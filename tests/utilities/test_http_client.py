import unittest
from unittest.mock import patch, Mock
from requests.exceptions import HTTPError
from src.mpyl.utilities.http_client.exceptions import (
    AuthorizationError,
    HTTPRequestError,
)
from src.mpyl.utilities.http_client import HttpClient


class TestHTTPClient(unittest.TestCase):
    def setUp(self):
        self.url = "https://example.com/"

    @patch("requests.Session")
    def test_callout_data_sucess(self, mock_session_class):
        expected_datas = [
            {"key1": "value1"},
            {"key2": "value2"},
            {"key3": "value3"},
            {"key4": "value4"},
            {"message": "deleted"},
        ]
        self.setup_success_mock_data(mock_session_class, expected_datas)
        http_client = HttpClient(base_url=self.url)
        result_1 = http_client.get("data")
        result_2 = http_client.post("search")
        result_3 = http_client.put("data/0")
        result_4 = http_client.patch("data/1")
        result_5 = http_client.delete("data/1")

        assert result_1.json() == expected_datas[0]
        assert result_2.json() == expected_datas[1]
        assert result_3.json() == expected_datas[2]
        assert result_4.json() == expected_datas[3]
        assert result_5.json() == expected_datas[4]

    @patch("requests.Session")
    def test_callout_raise_http_error(self, mock_session_class):
        error_respson = {"response": "error not found"}
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError(error_respson)
        mock_session_class.return_value.request.return_value = mock_response

        http_client = HttpClient(self.url)
        with self.assertRaises(HTTPRequestError) as err:
            http_client.get("data")

        assert (
            str(err.exception)
            == f"HTTP Request [GET] data response with an error: {error_respson}"
        )

    @patch("requests.Session")
    def test_callout_raise_general_error(self, mock_session_class):
        error_respson = {"response": "error not found"}
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception(error_respson)
        mock_session_class.return_value.request.return_value = mock_response

        http_client = HttpClient(self.url)
        with self.assertRaises(HTTPRequestError) as err:
            http_client.get("data")

        assert (
            str(err.exception)
            == f"HTTP Request [GET] data response with an error: Unknown Error {error_respson}"
        )

    @patch("requests.post")
    def test_fresh_token_raise_auth_error(self, mock_post):
        error_respson = "Bad Request"
        mock_post.side_effect = Exception(error_respson)

        token_url = "https://test.com/oauth/token"
        with self.assertRaises(AuthorizationError) as err:
            HttpClient.get_token_request(token_url, {})
        assert (
            f"HTTP Request [POST] {token_url} response with an error: Authorization error"
            in str(err.exception)
        )

    def setup_success_mock_data(self, mock_session_class, expected_datas) -> None:
        mock_responses = []
        for data in expected_datas:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = data
            mock_responses.append(mock_response)
        mock_session_class.return_value.request.side_effect = mock_responses
