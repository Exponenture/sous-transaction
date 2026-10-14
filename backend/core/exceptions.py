import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or {}}}


def exception_handler(exc, context):
    """Every error leaves the API as {"error": {"code", "message", "details"}}."""
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(getattr(exc, "message_dict", exc.messages))
    if isinstance(exc, IntegrityError):
        logger.warning("integrity_error: %s", exc)
        body = _body("conflict", "Request conflicts with existing data.")
        return Response(body, status.HTTP_409_CONFLICT)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("unhandled_error")
        return Response(
            _body("server_error", "Internal server error."), status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if isinstance(exc, exceptions.ValidationError):
        response.data = _body("validation_error", "Invalid input.", exc.detail)
    else:
        code = exc.get_codes() if isinstance(exc, exceptions.APIException) else "error"
        detail = getattr(exc, "detail", str(exc))
        response.data = _body(code if isinstance(code, str) else "error", str(detail))
    return response
