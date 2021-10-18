import sentry_sdk
from pecan.hooks import PecanHook


class SentryHook(PecanHook):
    def before(self, state):
        request = state.request
        sentry_sdk.set_context(
            "request",
            {
                "host": request.host,
                "method": request.method,
                "path": request.path_qs,
                # To ensure we don't submit an entire job
                "body": request.body[:1024],
            },
        )
