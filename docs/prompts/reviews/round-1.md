# Adversarial review round 1 (Codex)

Pasted into the Builder session. Triage of each finding is in `PLAN.md` step 9. Absolute local paths shortened to repo-relative.

```text
Verdict: BLOCK. Reviewed main...HEAD on feat/transactions; no repository files changed.
Verification: 206 tests pass, 13 admin tests fail. Lint passes; no missing migrations detected. Reproductions used small synthetic inputs, no live AI calls, and rolled-back database writes.
Severity	Dimension / location	What breaks	Suggested fix	Confidence
BLOCKER	Completeness / CI — [admin contract (line 38)](backend/tests/test_transaction_admin.py:38)	Transaction admin registration is absent. All 13 admin tests fail; the review queue and approve/reject flow are unavailable.	Implement the approved admin slice before merging.	High
MAJOR	Validation / errors — [validation.py (line 70)](backend/transactions/validation.py:70)	Amount "1e1000000" raises decimal.Overflow during abs(amount). It escapes validation instead of producing an invalid_amount quarantine issue.	Handle decimal arithmetic exceptions as invalid input.	High; reproduced
MAJOR	Persistence / dirty input — [services.py (line 74)](backend/transactions/services.py:74)	An unknown key containing "\u0000" passes validation, but PostgreSQL JSONB cannot store it. POST returns 500 and loses the submission.	Agree a storage-safe raw-payload policy and handle unsupported characters explicitly.	High; reproduced
MAJOR	Categorisation — [categorisation.py (line 85)](backend/transactions/categorisation.py:85)	Fallback classifies "Salary from School Employer" as Education and "Transfer to Rent Account" as Housing. This contradicts the specified Miscellaneous policy for non-spending movements.	Apply movement classification before spending keywords, with clear precedence.	High; reproduced
MAJOR	Provider failure handling — [categorisation.py (line 96)](backend/transactions/categorisation.py:96)	The Anthropic constructor sits outside the exception handler. If client initialisation fails, the request fails instead of falling back to rules.	Include client construction in the protected provider operation.	High; reproduced with mock
MAJOR	Submission documentation — [README.md (line 1)](README.md:1)	README still describes the scaffold. Transaction examples, quarantine/replay behaviour, algorithm, prompts, trade-offs, and framework reasoning are missing.	Complete the documentation slice before submission.	High


Checked and holds, or remains unverified:
- Ownership: API querysets scope to the caller at [views.py (line 23)](backend/transactions/views.py:23); cross-user tests pass. Admin isolation remains unverified.
- Authentication: endpoints inherit IsAuthenticated and JWT-first authentication from [settings.py (line 84)](backend/config/settings.py:84); permission tests pass. Endpoint-level explicit permission declarations are still absent.
- Integrity/concurrency: per-owner uniqueness and category/type/status constraints exist at [models.py (line 76)](backend/transactions/models.py:76). Concurrent replay tests pass; writes use an atomic block.
- Idempotency: sequential replay skips categorisation; conflicting payloads return 409. Concurrent first submissions can both call AI before uniqueness resolves the race at [services.py (line 48)](backend/transactions/services.py:48).
- Performance: pagination limits responses; serializers introduce no relationship-query loop. AI calls occur outside database transactions. Load behaviour and AI latency under contention are unverified.
- Scalability: synchronous AI calls occupy request workers; async processing is explicitly deferred in [PLAN.md (line 87)](PLAN.md:87). No load test was performed.
- Migrations: [0001_initial.py (line 18)](backend/transactions/migrations/0001_initial.py:18) creates a new table; there is no hot-table alteration or data migration. Migration consistency passes.
- Privacy: provider context excludes account number and owner at [categorisation.py (line 97)](backend/transactions/categorisation.py:97); clean/dirty log-redaction tests pass. Exceptional-path redaction needs coverage.
- Observability: stored-row logs contain IDs/status/issue codes at [services.py (line 82)](backend/transactions/services.py:82); fallback failures log exception classes. Alert delivery is unverified.
- Test quality: current tests exercise negative cases, ownership, retries, and PostgreSQL races. Missing cases below explain why the reproduced defects escaped.
- Simplicity: the model/validation/service/provider split is proportionate. No deletion-worthy abstraction identified.
Missing tests:
- Extreme decimal exponents produce quarantine issues without 500.
- NUL characters in recognised and unknown fields follow the agreed storage policy.
- Salary, transfers, and refunds containing spending keywords remain Miscellaneous.
- Provider constructor failure triggers fallback.
- Concurrent duplicate requests verify the agreed AI-call policy.
- Approved wrong-JSON-type examples, expired JWTs, and equal-timestamp ordering.
- OpenAPI contract and Docker startup smoke checks.
Questions for the Lead:
- How should raw payload preserve JSON values PostgreSQL cannot represent?
- Is duplicate AI work during concurrent identical requests acceptable?
- May reviewers access all users’ transactions, or must admin permissions restrict ownership?
This review was performed in the same chat that authored the tests. It does not satisfy the repository’s independent, fresh-thread reviewer requirement.
```
