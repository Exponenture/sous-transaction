# Tester's proposed test plan (Codex)

Pasted into the Builder session for review before tests were written. The Builder's review led to spec amendments AM1–AM5.

| Proposed test file | Behaviour to prove |
|---|---|
| `test_submission.py` | Clean submission returns `201`; correct response fields; money represented as a two-decimal string; default currency is EUR; input normalisation; unknown keys preserved in raw payload |
| `test_quarantine.py` | Every blocking validation rule produces the correct issue; dirty input is stored; issues accumulate; successfully parsed fields survive; invalid fields become null where specified |
| `test_timestamps.py` | Amsterdam interpretation of naive timestamps; explicit offsets respected; DST gap quarantined; overlap uses first occurrence with warning; five-minute future boundary |
| `test_idempotency.py` | Identical replay returns `200` and original result; changed payload returns `409`; keys scoped per owner; invalid/missing keys have no replay protection; concurrent replay creates one row |
| `test_retrieval.py` | Detail retrieval for every status; exact response contract; raw payload only on detail; default categorised list; status/category filters; invalid filters; pagination and ordering |
| `test_permissions.py` | Authentication required on all three endpoints; cross-user list isolation; another user’s ID and malformed/unknown UUID return `404`; owner cannot be overridden |
| `test_categorisation.py` | Rules produce allowed categories; unknown description becomes Miscellaneous; usable descriptions are categorised even on quarantined rows; unusable descriptions produce no category |
| `test_llm.py` | Valid AI result; off-list/malformed responses; timeout/provider failure; absent API key; rules fallback and warning; five-second timeout; no retries; sensitive fields excluded |
| `test_constraints.py` | Database independently enforces category/type/status values, required fields for categorised rows, per-owner uniqueness, and protected owner deletion |
| `test_admin_review.py` | Staff permissions; filters; approve only after successful revalidation; reject transition; review attribution; raw payload read-only |
