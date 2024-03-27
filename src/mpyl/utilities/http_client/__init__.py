"""Generic Http Client for handling requests"""

import requests
from requests.exceptions import RequestException, HTTPError
from .exceptions import AuthorizationError, HTTPRequestError


class HttpClient:
    def __init__(self, base_url, refresh_token=None) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.refresh_token = refresh_token

    def get(self, endpoint, params=None, headers=None):
        return self._request("GET", endpoint, params, headers=headers)

    def post(self, endpoint, data=None, json=None, headers=None):
        return self._request("POST", endpoint, data=data, json=json, headers=headers)

    def put(self, endpoint, data=None, json=None, headers=None):
        return self._request("PUT", endpoint, data=data, json=json, headers=headers)

    def patch(self, endpoint, data=None, json=None, headers=None):
        return self._request("PATCH", endpoint, data=data, json=json, headers=headers)

    def delete(self, endpoint, headers=None):
        return self._request("DELETE", endpoint, headers=headers)

    @staticmethod
    def get_token_request(token_url, credentials) -> requests.Response:
        try:
            response = requests.post(token_url, data=credentials, timeout=3)
            response.raise_for_status()
            return response
        except Exception as err:
            raise AuthorizationError(
                method="POST", url=token_url, message=f"Authorization error {err}"
            ) from err

    def _request(
        self, method, endpoint, params=None, data=None, json=None, headers=None
    ):
        if headers is None:
            headers = {}

        if self.refresh_token is not None and callable(self.refresh_token):
            auth_header = self.refresh_token()
            if auth_header is not None:
                headers.update(auth_header)
        try:
            response = self.session.request(
                method,
                self.base_url + endpoint,
                params=params,
                data=data,
                json=json,
                headers=headers,
            )
            response.raise_for_status()
            return response
        except HTTPError as err:
            raise HTTPRequestError(method=method, url=endpoint, error=err) from err
        except TimeoutError as err:
            raise HTTPRequestError(
                method=method, url=endpoint, message=f"Request time out {err}"
            ) from err
        except RequestException as err:
            raise HTTPRequestError(method=method, url=endpoint, error=err) from err
        except Exception as err:
            raise HTTPRequestError(
                method=method, url=endpoint, message=f"Unknown Error {err}"
            ) from err
