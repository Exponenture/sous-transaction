from django.contrib import admin, messages

from transactions import services
from transactions.models import Transaction
from transactions.validation import ISSUE_CODES

EDITABLE = (
    "transaction_id",
    "amount",
    "currency",
    "timestamp",
    "description",
    "transaction_type",
    "account_number",
    "category",
)
READ_ONLY = (
    "id",
    "owner",
    "status",
    "categorisation_source",
    "issues",
    "raw_payload",
    "reviewed_by",
    "reviewed_at",
    "created_at",
)


class IssueCodeFilter(admin.SimpleListFilter):
    title = "issue"
    parameter_name = "issue"

    def lookups(self, request, model_admin):
        return [(code, code) for code in ISSUE_CODES]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(issues__contains=[{"code": self.value()}])
        return queryset


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Human review queue: fix fields on a quarantined row, then approve or reject it."""

    list_display = (
        "transaction_id",
        "owner",
        "amount",
        "transaction_type",
        "timestamp",
        "category",
        "status",
        "issue_codes",
    )
    list_filter = ("status", IssueCodeFilter, "category", "categorisation_source")
    list_select_related = ("owner",)
    search_fields = ("transaction_id", "description")
    fields = READ_ONLY[:4] + EDITABLE + READ_ONLY[4:]
    actions = ["approve", "reject"]

    @admin.display(description="Issues")
    def issue_codes(self, obj):
        return ", ".join(issue["code"] for issue in obj.issues) or "-"

    def get_readonly_fields(self, request, obj=None):
        # Only quarantined rows are under review; everything else is a record, not a draft.
        if obj is None or obj.status == Transaction.Status.QUARANTINED:
            return READ_ONLY
        return READ_ONLY + EDITABLE

    def has_add_permission(self, request):
        return False  # rows arrive through the API only

    def has_delete_permission(self, request, obj=None):
        return False  # reject instead; keeps the audit trail

    @admin.action(
        description="Approve selected (re-validate, quarantined only)", permissions=["change"]
    )
    def approve(self, request, queryset):
        self._review(request, queryset, services.approve_transaction, "approved")

    @admin.action(description="Reject selected (quarantined only)", permissions=["change"])
    def reject(self, request, queryset):
        self._review(request, queryset, services.reject_transaction, "rejected")

    def _review(self, request, queryset, action, verb):
        done, still_invalid, skipped = 0, [], 0
        for pk in queryset.values_list("pk", flat=True):
            row, changed = action(pk=pk, reviewer=request.user)
            if changed:
                done += 1
            elif row.status == Transaction.Status.QUARANTINED:
                still_invalid.append(row)
            else:
                skipped += 1
        if done:
            self.message_user(request, f"{done} transaction(s) {verb}.", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} skipped: not quarantined.", messages.WARNING)
        for row in still_invalid:
            codes = ", ".join(i["code"] for i in row.issues if i["severity"] == "blocking")
            self.message_user(request, f"{row} still has blocking issues: {codes}", messages.ERROR)
