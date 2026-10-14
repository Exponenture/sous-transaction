from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TimestampedModel


class Status(models.TextChoices):
    CATEGORISED = "categorised"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class Type(models.TextChoices):
    DEBIT = "debit"
    CREDIT = "credit"


class Category(models.TextChoices):
    GROCERIES = "Groceries"
    DINING_OUT = "Dining Out"
    UTILITIES = "Utilities"
    TRANSPORTATION = "Transportation"
    ENTERTAINMENT = "Entertainment"
    HEALTHCARE = "Healthcare"
    SHOPPING = "Shopping"
    HOUSING = "Housing"
    EDUCATION = "Education"
    MISCELLANEOUS = "Miscellaneous"


class Source(models.TextChoices):
    LLM = "llm"
    RULES = "rules"
    NONE = "none"


class Transaction(TimestampedModel):
    """A submitted bank transaction. Unparseable fields are null and the row is quarantined."""

    Status = Status
    Type = Type
    Category = Category
    Source = Source

    # Null (not "") means "absent or unparseable" on quarantined rows, so CharFields are nullable.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_id = models.CharField(max_length=64, null=True, blank=True)  # noqa: DJ001
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True, default="EUR")  # noqa: DJ001
    timestamp = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    transaction_type = models.CharField(  # noqa: DJ001
        max_length=16, choices=Type.choices, null=True, blank=True
    )
    account_number = models.CharField(max_length=34, null=True, blank=True)  # noqa: DJ001
    category = models.CharField(  # noqa: DJ001
        max_length=20, choices=Category.choices, null=True, blank=True
    )
    categorisation_source = models.CharField(max_length=5, choices=Source.choices)
    status = models.CharField(max_length=11, choices=Status.choices)
    issues = models.JSONField(default=list, blank=True)
    raw_payload = models.JSONField()
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "transaction_id"], name="transaction_unique_owner_client_id"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in Status]), name="transaction_status_valid"
            ),
            models.CheckConstraint(
                condition=Q(categorisation_source__in=[s.value for s in Source]),
                name="transaction_source_valid",
            ),
            models.CheckConstraint(
                condition=Q(category__isnull=True) | Q(category__in=[c.value for c in Category]),
                name="transaction_category_valid",
            ),
            models.CheckConstraint(
                condition=Q(transaction_type__isnull=True)
                | Q(transaction_type__in=[t.value for t in Type]),
                name="transaction_type_valid",
            ),
            models.CheckConstraint(
                condition=~Q(status="categorised")
                | Q(
                    amount__isnull=False,
                    currency__isnull=False,
                    timestamp__isnull=False,
                    description__isnull=False,
                    transaction_type__isnull=False,
                    account_number__isnull=False,
                    category__isnull=False,
                ),
                name="transaction_categorised_complete",
            ),
        ]
        indexes = [
            models.Index(
                fields=["owner", "status", "timestamp"], name="transaction_owner_status_ts"
            )
        ]

    def __str__(self):
        return f"{self.transaction_id or self.pk} ({self.status})"
