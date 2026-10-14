import logging

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@extend_schema(responses={200: dict, 503: dict})
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("health_db_unreachable")
        body = {"status": "error", "db": "down"}
        return Response(body, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"status": "ok", "db": "ok"})
