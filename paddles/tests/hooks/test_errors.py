from webob import exc

from paddles.exceptions import APIError, InvalidRequestError
from paddles.hooks.errors import (
    PaddlesErrorHook,
    json_error_response,
    redirect_error,
)


class TestPaddlesErrorHook:
    def test_api_error_carries_url_and_message(self):
        exc = APIError("/errors/invalid/", "bad input")
        assert exc.url == "/errors/invalid/"
        assert str(exc) == "bad input"

    def test_invalid_request_error_uses_default_url(self):
        exc = InvalidRequestError("missing field")
        assert exc.url == "/errors/invalid/"
        assert str(exc) == "missing field"

    def test_json_error_response(self):
        response = json_error_response(404, "missing")
        assert response.status_int == 404
        assert response.content_type == "application/json"
        assert response.json_body == {"message": "missing"}

    def test_hook_handles_http_exception(self):
        hook = PaddlesErrorHook()

        class State:
            pass

        response = hook.on_error(State(), exc.HTTPNotFound())
        assert response.status_int == 404
        assert response.content_type == "application/json"
        assert "message" in response.json_body

    def test_hook_handles_unhandled_exception(self):
        hook = PaddlesErrorHook()

        class State:
            pass

        response = hook.on_error(State(), RuntimeError("boom"))
        assert response.status_int == 500
        assert response.content_type == "application/json"
        assert response.json_body == {"message": "internal server error"}

    def test_hook_handles_paddles_error(self, monkeypatch):
        redirected = []

        def fake_redirect(url, internal=True):
            redirected.append((url, internal))
            raise SystemExit("redirect")

        monkeypatch.setattr("paddles.hooks.errors.redirect", fake_redirect)
        monkeypatch.setattr(
            "paddles.hooks.errors.request",
            type("R", (), {"context": {}})(),
        )

        hook = PaddlesErrorHook()
        try:
            redirect_error(InvalidRequestError("nope"))
        except SystemExit:
            pass

        assert redirected[0][0].startswith("/errors/invalid/")
        assert "nope" in redirected[0][0]

        class State:
            pass

        redirected.clear()
        try:
            hook.on_error(State(), InvalidRequestError("via hook"))
        except SystemExit:
            pass
        assert redirected[0][0].startswith("/errors/invalid/")
