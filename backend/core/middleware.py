import contextvars
import logging
import re
import uuid

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_VALID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestIDMiddleware:
    """Accept a sane inbound X-Request-ID or mint one; expose it on request, logs and response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        rid = incoming if _VALID.match(incoming) else uuid.uuid4().hex
        request.request_id = rid
        # Not reset on exit: Django's request logger fires after the middleware chain returns.
        request_id_var.set(rid)
        response = self.get_response(request)
        response["X-Request-ID"] = rid
        return response


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True
