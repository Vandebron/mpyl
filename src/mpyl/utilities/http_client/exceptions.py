"""Http Request Error Type"""


class HTTPRequestError(Exception):
    def __init__(self, method, url, message="Unknown", error=None):
        if error is not None and error.response is not None:
            self.message = f"HTTP Request [{method}] {url} response with an error: {error.response.text}"
        elif error is not None:
            self.message = (
                f"HTTP Request [{method}] {url} response with an error: {error}"
            )
        else:
            self.message = (
                f"HTTP Request [{method}] {url} response with an error: {message}"
            )
        super().__init__(self.message)


class AuthorizationError(HTTPRequestError):
    pass
