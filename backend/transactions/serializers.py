from rest_framework import serializers

from transactions.models import Transaction

ALL = "all"


class IssueSerializer(serializers.Serializer):
    code = serializers.CharField()
    field = serializers.CharField(allow_null=True)
    severity = serializers.ChoiceField(choices=["blocking", "warning"])
    message = serializers.CharField()


class TransactionSerializer(serializers.ModelSerializer):
    issues = IssueSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_id",
            "amount",
            "currency",
            "timestamp",
            "description",
            "transaction_type",
            "account_number",
            "category",
            "categorisation_source",
            "status",
            "issues",
            "created_at",
        ]
        read_only_fields = fields


class TransactionDetailSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        fields = [*TransactionSerializer.Meta.fields, "raw_payload"]
        read_only_fields = fields


class TransactionListParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[*Transaction.Status.values, ALL], default=Transaction.Status.CATEGORISED
    )
    category = serializers.ChoiceField(choices=Transaction.Category.values, required=False)


class TransactionSubmissionSerializer(serializers.Serializer):
    """Documents the POST body for OpenAPI only. Validation happens in validation.py, because
    dirty input is quarantined rather than rejected."""

    transaction_id = serializers.CharField(max_length=64)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    timestamp = serializers.CharField(help_text="ISO 8601; no offset = Europe/Amsterdam.")
    description = serializers.CharField(max_length=255)
    transaction_type = serializers.ChoiceField(choices=Transaction.Type.values)
    account_number = serializers.CharField(max_length=34)
    currency = serializers.CharField(max_length=3, required=False, default="EUR")
