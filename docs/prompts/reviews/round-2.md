# Adversarial review round 2 (Codex)

Pasted into the Builder session. Triage of each finding is in `PLAN.md` step 9. Absolute local paths shortened to repo-relative.

```text
1. Verdict: BLOCK
2. Findings, most severe first
Severity	Dimension	file:line	What breaks	Suggested fix	Confidence
MAJOR	Data integrity / spec	[validation.py (line 88)](backend/transactions/validation.py:88), [validation.py (line 77)](backend/transactions/validation.py:77)	Sanitisation silently overwrites colliding keys. Reproduced {"extra\u0000":"lost","extra�":"kept"} becoming {"extra�":"kept"}; nested objects behave identically. The discarded value disappears from the review record and replay comparison, violating the dirty-data preservation contract.	Detect collisions at every depth before assigning keys. Obtain a Lead-approved policy that preserves the conflicting values and defines replay equality.	High; reproduced
MAJOR	Security / errors / spec	[validation.py (line 71)](backend/transactions/validation.py:71)	A valid JSON object containing 600 nested arrays parses successfully but raises RecursionError during sanitisation—even under an unknown key. Because sanitisation runs before validation, the submission fails instead of being quarantined.	Replace recursive traversal with an iterative approach; verify the full parse, storage, and response path handles the supported nesting depth.	High; sanitiser reproduced, HTTP response inferred


3. Checked and holds
- Multi-tenancy: API querysets and replay lookups filter by owner ([views.py (line 25)](backend/transactions/views.py:25), [services.py (line 58)](backend/transactions/services.py:58)). Cross-owner admin access remains the explicitly accepted R8 deferral in [PLAN.md (line 50)](PLAN.md:50).
- AuthN/AuthZ: Explicit IsAuthenticated on the viewset; expired-token regressions cover all supported operations ([views.py (line 21)](backend/transactions/views.py:21), [regressions:139 (line 139)](backend/tests/test_transaction_review_regressions.py:139)).
- Idempotency/external calls: Owner/key uniqueness, atomic insertion, and race recovery remain intact; duplicate concurrent AI calls are the accepted R7 tradeoff ([services.py (line 77)](backend/transactions/services.py:77)). Constructor failures now enter fallback; timeout and retries remain bounded ([categorisation.py (line 106)](backend/transactions/categorisation.py:106)).
- Performance: List results remain paginated, serializers introduce no related-object loops, and AI calls occur before database transactions ([views.py (line 19)](backend/transactions/views.py:19), [services.py (line 62)](backend/transactions/services.py:62)).
- Scalability: No new shared locks, jobs, or hot rows; sanitisation traverses the submitted payload. Behavior at 10×/100× traffic is unverified ([validation.py (line 66)](backend/transactions/validation.py:66)).
- Migration safety: No schema or migration changes; makemigrations --check --dry-run reports no changes. Existing constraints remain ([models.py (line 75)](backend/transactions/models.py:75)).
- Test quality: Added regressions cover ordinary AM6 nesting/replay and AM7 fixes, without weakening existing tests; concurrent insertion coverage remains ([regressions:50 (line 50)](backend/tests/test_transaction_review_regressions.py:50), [integrity:88 (line 88)](backend/tests/test_transaction_integrity.py:88)).
- Simplicity: Changes stay within the approved fixes and smoke coverage; no speculative abstraction or dead code identified ([categorisation.py (line 33)](backend/transactions/categorisation.py:33), [docker_smoke.py (line 26)](backend/tests/docker_smoke.py:26)).
Security, error handling, data integrity, and spec conformance have the findings above.
4. Missing tests
- Top-level and nested NUL/replacement-key collisions preserve both values under the approved policy.
- Changing a value involved in a collision cannot incorrectly produce an identical replay.
- Deeply nested unknown JSON fields, with and without NUL, complete without a 500.
5. Questions for the Lead
- How should AM6 represent two distinct keys that become identical after sanitisation, and how should those payloads compare for replay?
Validation: 239 tests passed, Ruff lint/format passed, migration check passed. Docker smoke execution and remote CI status are unverified.
```
