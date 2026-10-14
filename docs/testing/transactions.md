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

`test_transaction_admin.py` now covers anonymous/non-staff access, staff without
model permission, corrected-field approval, failed approval with an admin error,
reviewer/time attribution, rejection, actions restricted to quarantined rows,
read-only raw payload, status/issue filters, rejected retrieval and replay.
It uses one dirty transaction per test and a second clean row only for filtering.
Action identifiers and issue-filter parameters are discovered from the admin UI
rather than hard-coded. The transaction admin registration is currently missing,
so these tests intentionally fail at URL resolution until slice 3 is built.

## Adversarial-review regressions (AM6–AM7)

`test_transaction_review_regressions.py` pins decimal-overflow quarantine,
recursive NUL sanitisation (keys and values), one unsupported-character issue per
top-level field, replay against sanitised JSON, movement-before-spending precedence,
constructor-failure fallback and wrong-type handling. It also checks expired JWTs,
equal-timestamp creation ordering and the generated OpenAPI contract.

The Docker smoke job runs `backend/tests/docker_smoke.py` against a disposable
`sous-ci-smoke` Compose project in GitHub Actions and Bitbucket Pipelines. It uses
two synthetic transactions, no AI key, and checks health, real JWT authentication,
creation, replay, detail and quarantine filtering. It removes its disposable volumes
afterwards. Docker CI execution has not been verified locally.

Concurrent duplicate AI-call policy and admin ownership policy remain Lead decisions;
no tests invent those contracts. Exceptional-path log redaction still needs coverage.
