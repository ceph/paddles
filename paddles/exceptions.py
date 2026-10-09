class PaddlesError(Exception):
    url = ""

    def __init__(self, message=""):
        super().__init__(message)


class APIError(PaddlesError):
    """Raised to redirect to a JSON errors endpoint."""

    def __init__(self, url, message=None):
        self.url = url
        self.message = message
        super().__init__(message or "")


class InvalidRequestError(PaddlesError, ValueError):
    url = "/errors/invalid/"


class ForbiddenRequestError(PaddlesError, RuntimeError):
    url = "/errors/forbidden/"


class ResourceNotFoundError(PaddlesError, ValueError):
    url = "/errors/not_found/"


class ResourceUnavailableError(PaddlesError, RuntimeError):
    url = "/errors/unavailable/"
