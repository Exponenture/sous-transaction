from django.db.models import F
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, mixins, status, viewsets
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from transactions import services
from transactions.models import Transaction
from transactions.serializers import (
    ALL,
    TransactionDetailSerializer,
    TransactionListParamsSerializer,
    TransactionSerializer,
    TransactionSubmissionSerializer,
)


class TransactionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    parser_classes = [JSONParser]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.filter(owner=self.request.user)
        if self.action != "list":
            return queryset
        params = TransactionListParamsSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        if params.validated_data["status"] != ALL:
            queryset = queryset.filter(status=params.validated_data["status"])
        if "category" in params.validated_data:
            queryset = queryset.filter(category=params.validated_data["category"])
        return queryset.order_by(F("timestamp").desc(nulls_last=True), "-created_at")

    def get_serializer_class(self):
        return TransactionDetailSerializer if self.action == "retrieve" else TransactionSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("status", enum=[*Transaction.Status.values, ALL]),
            OpenApiParameter("category", enum=Transaction.Category.values),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=TransactionSubmissionSerializer,
        responses={201: TransactionSerializer, 200: TransactionSerializer},
        description="Dirty input is stored with status=quarantined and labelled issues. "
        "Replaying the same transaction_id with an identical payload returns 200.",
    )
    def create(self, request):
        if not isinstance(request.data, dict):
            raise exceptions.ValidationError({"body": ["Must be a JSON object."]})
        row, created = services.submit_transaction(owner=request.user, payload=request.data)
        return Response(
            TransactionSerializer(row).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
