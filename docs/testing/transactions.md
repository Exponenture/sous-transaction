# Transaction contract tests

These tests use the approved `NOTES.md`, not the transaction implementation.
GitHub Actions already discovers `backend/tests/test_*.py` through its existing
`pytest` step and runs against PostgreSQL 16. No workflow change is necessary.

Run the gate with `make test lint`. Before the Builder implements transactions,
these contract tests are expected to fail because `/api/transactions/` is absent;
CI must remain red until the implementation satisfies them. No skips or expected
failures conceal missing functionality.

## Covered contracts

- Submission and exact public response fields; detail-only raw JSON payload.
- Decimal precision, boundaries, normalisation and preserved original values.
- Required fields, every listed blocking validation code, accumulated issues,
  retained parsed fields and unusable descriptions.
- Amsterdam timezone, explicit offsets, DST gap/overlap and future-time boundary.
- Rules fallback without credentials and no category for unusable descriptions.
- Replay, payload conflicts, invalid/missing keys, owner scope and concurrent replay.
- Authentication, ownership, server-controlled fields and unsupported mutations.
- Status/category filters, pagination, timestamp ordering and nulls last.
- PostgreSQL category/type/status/not-null constraints, uniqueness and owner protection.

Future timestamps use now + 4 / + 6 minutes per AM5, without freezing time.
Tests clear ANTHROPIC_API_KEY in the process environment and Django settings.
AI-specific tests supply a dummy key and mock the constructor specified in AM1. Ordinary requests use `auth_client`;
unauthenticated tests exercise the actual permission boundary. Concurrency uses
separate connections and a transactional test against PostgreSQL.

## Explicit test assumptions for Lead review

- Issues use severity strings `blocking` and `warning`, matching the spec headings.
- The six listed non-currency input fields, including transaction_id, are required.
- raw_payload is the decoded JSON object, preserving values and unknown keys.
- A description exceeding the storage limit is unusable for categorisation.
- `ANTHROPIC_API_KEY` is the configuration name for the Anthropic credential.
- List pagination uses DRF's existing count/next/previous/results envelope.

## Amendment coverage (AM1–AM5)

`test_transaction_edge_cases.py` covers the approved sample-description mapping,
case-insensitive whole-word rules, every allowed AI result, off-list/malformed/empty
AI responses, exceptions/timeouts, timeout/retry configuration, no-key bypass,
provider PII exclusion and replay avoiding another provider call. It also covers
raw JSON equality (key order, numeric equality and string-vs-number conflict),
malformed JSON, unsupported collection mutations and clean/dirty log redaction.
Missing AI implementation produces visible setup failures; nothing is skipped.

Wrong field types not specified by the validation table and overlapping keyword
precedence still need a Lead decision. The response fake uses Anthropic text blocks
containing a JSON object with a category property; this is the SDK response shape
assumed for the AM1 structured-output contract.

## Remaining suites for later plan slices

Before slice 3, specify admin action identifiers and issue-filter parameters, then
add admin HTTP tests for staff permissions, approve/reject, revalidation, review
attribution and read-only raw payload. Add rejected-record retrieval assertions
through that review flow.

Also outstanding: equal-timestamp creation-order tests with distinct creation
instants, expired JWT tests, OpenAPI contracts and a Docker
Compose smoke check. These are not represented as completed by this first suite.
