"""Http requests to Camunda modeler"""

import time
from collections import namedtuple
from ....utilities.http_client.exceptions import AuthorizationError
from ....utilities.http_client import HttpClient


class CamundaModelerClient:
    Token = namedtuple("Token", ["access_token", "expiration_time", "token_type"])

    def __init__(self, base_url, token_url, credentials):
        self.token_url = token_url
        self.credentials = credentials
        self.token = None
        self.http = HttpClient(base_url=base_url, refresh_token=self.refresh_token)

    def refresh_token(self) -> dict[str, str]:
        if (
            self.token is None
            or self.token.expiration_time is None
            or time.time() >= self.token.expiration_time
        ):
            self._get_token()

        if isinstance(self.token, self.Token):
            return {
                "Authorization": f"{self.token.token_type} {self.token.access_token}"
            }
        raise AuthorizationError(
            method="POST",
            url=self.token_url,
            message="Authorization error: no access_token found",
        )

    def _get_token(self) -> None:
        res = HttpClient.get_token_request(self.token_url, self.credentials).json()
        expiration_time = time.time() + res.get("expires_in")
        self.token = self.Token(
            res.get("access_token"), expiration_time, res.get("token_type")
        )

    def get_files(self, data):
        endpoint = "files/search"
        return self.http.post(endpoint=endpoint, json=data).json()

    def update_file_in_modeler(self, file_id, data):
        endpoint = f"files/{file_id}"
        return self.http.patch(endpoint=endpoint, json=data).json()

    def create_milestone_in_modeler(self, data):
        endpoint = "milestones"
        return self.http.post(endpoint=endpoint, json=data).json()
