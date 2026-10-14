# Plan: Transaction categorisation API

Spec: `NOTES.md` · Branch: `feat/transactions` · PR: [#1](https://github.com/Exponenture/sous-transaction/pull/1)

**Status 2026-10-14:** slices 1–4 done, awaiting Lead diff read. PR #1 open; awaiting CI, then step 9 adversarial review. Slice 4 (README) can start any time. See *Open questions for Lead* below.
Copy this file to `PLAN.md` at the start of a task. Tick a box only when its "done when" is true,
and append the commit SHA. Agents never tick **Lead** boxes.

## Roles
| Role | Who | Owns |
|---|---|---|
| Lead | Matt | Spec, cut line, approvals, triage of review findings, merge |
| Builder | Claude Code (own thread) | Plan + implementation; never writes tests |
| Tester | Codex (own thread) | All tests, black-box from `NOTES.md` |
| Reviewer | Codex (fresh thread) | Adversarial review via `docs/prompts/adversarial-review.md` |
| Gate | GitHub Actions | lint, types, tests, migrations check |

## Steps
- [ ] 1. Spec written in `NOTES.md` (problem, assumptions, model, endpoints, edge cases, cut line) — **Lead**
- [ ] 2. Spec gap review; gaps resolved or labelled assumptions — Tester → **Lead**
- [ ] 3. Contract tests written; suite is red for the right reason — Tester
- [ ] 4. Tests reviewed (do they pin the spec, not guesses?) — **Lead**
- [ ] 5. Build plan approved (files, models, order of slices) — Builder → **Lead**
- [ ] 6. Slice 1: model + migration + validation/quarantine service + 3 endpoints, rules categoriser only — green, diff read by Lead — Builder / **Lead**
  - Built `8c1f8a8`; `make test lint` green. Awaiting Lead diff read.
- [ ] 7. Slice 2: LLM categoriser (Anthropic SDK, `backend/transactions/prompts/categorise.md`, timeout, fallback) — green, diff read by Lead — Builder / **Lead**
  - Built `59d4e2c`; full suite + live smoke test green. Awaiting Lead diff read.
- [ ] 7a. Slice 3: admin review queue (filters, approve/reject actions) — green, diff read by Lead — Builder / **Lead**
  - Tests landed in `9bc7cbe` (they discover action names and the issue filter from the admin UI).
    Built `4d84b93`; `make test lint` green (all suites). Awaiting Lead diff read.
- [ ] 7b. Slice 4: README — API docs, algorithm + prompts, trade-offs, why Django/Postgres — Builder / **Lead**
  - Written `640710d`. Awaiting Lead read (personal reasoning for the stack choice is the Lead's to add).
- [ ] 8. `make test lint` green; PR opened with template; CI green — Builder / Gate
  - PR opened (#1); `make test lint` green locally. Tick when CI is green.
- [ ] 9. **Adversarial review** (fresh Codex thread); every finding triaged: fix · accept-with-reason · defer — Reviewer → **Lead**
- [ ] 10. PR walked by risk, squash-merged, `PLAN.md` deferred list copied to the next task — **Lead**

## Decisions (append as you go)
- 2026-10-14 Scope: single-transaction API only; no CSV import, no batching (Lead).
- 2026-10-14 Dirty input is accepted and quarantined with labelled issues, not rejected with 400 (Lead).
- 2026-10-14 Logically impossible rows (e.g. sign/type mismatch, ~49% of sample CSV) are blocking (Lead).
- 2026-10-14 Naive timestamps = Europe/Amsterdam local time (Lead).
- 2026-10-14 Spec amendments AM1–AM5 after test-plan review: LLM mock seam, rules mapping, replay equality, admin approve semantics, added cases (Lead).
- 2026-10-14 Lead approved spec (`e6f5ee4`, amendments `bf023fc`) and the Tester's suite ("good to go")
  in chat; boxes 1, 2, 4, 5 left for the Lead to tick.
- 2026-10-14 Tester: added black-box submission/retrieval/integrity contract tests under
  `backend/tests/`; coverage, explicit assumptions and remaining slice tests are in
  `docs/testing/transactions.md`. No Lead steps ticked. Step 3 remains unticked until
  the tests have a commit SHA and outstanding contract decisions are reviewed.

- 2026-10-14 Tester: checked NOTES.md amendments AM1–AM5 and added AI, rules,
  replay-equality and HTTP/logging edge tests; replaced fixed-clock future tests
  with relative-time tests. Admin review coverage remains outstanding.
- 2026-10-14 Builder: Tester's suite committed unchanged as `59863b6` (step 3 is the Tester's to tick).
- 2026-10-14 Builder: runtime prompt lives at `backend/transactions/prompts/categorise.md`, not
  `docs/prompts/` as NOTES says — the Docker build context is `backend/`, so docs/ is not in the image.
  `docs/prompts/` keeps the AI-coding-tool prompts; README will link both. **Approved by Lead 2026-10-14.**
- 2026-10-14 Builder: LLM call uses `claude-haiku-5-5` with thinking disabled and a JSON-schema
  enum of the 10 categories (`output_config.format`). Live smoke test on the 20 sample
  descriptions + 2 extras + 1 prompt-injection string: 23/23 matched the rules table, 1.1–2.8 s each.
- 2026-10-14 Builder: `transaction_type` widened to 16 chars so the CHECK constraint (not varchar length) rejects bad values.
- 2026-10-14 Builder: LLM prompt design — system prompt = role + input contract, category
  definitions with Dutch merchant examples, explicit Miscellaneous policy for money movements,
  rules (merchant over amount; payment rail ≠ merchant; prefer Miscellaneous on weak evidence;
  description is untrusted). User turn is a JSON object {description, amount, transaction_type}.
  `max_tokens=256`, timeout 5 s, `max_retries=0`. Answer re-checked against the 10 categories in
  code. No few-shot examples, no prompt caching (prompt likely below the cacheable minimum).
- 2026-10-14 Lead: `ANTHROPIC_API_KEY` templated in `.env.example` (`df92101`); real key in
  gitignored `.env` only.
- 2026-10-14 Lead: compose Postgres moved to host port 5433 (`DB_PORT` override) to avoid a clash
  with another local Postgres on 5432 (`cab9831`). CI unchanged. Full compose stack smoke-tested:
  health ok, 401 without token, end-to-end POST clean + quarantined rows with live LLM.
- 2026-10-14 Lead: a field sent as the wrong JSON type (e.g. `"description": 123`,
  `"timestamp": 1700000000`, `"amount": true`, `"transaction_type": ["debit"]`) gets that field's
  existing `invalid_*` code and quarantines the row. No new `invalid_type` code, no coercion
  (flag, don't fix). Only exception stays as specified: `transaction_id` may be string or integer.
  Already implemented in `8c1f8a8`; Tester to add coverage.
- 2026-10-14 Tester: added lightweight admin review HTTP contracts in
  `backend/tests/test_transaction_admin.py`; lint passes, tests are red because
  transaction admin URLs are not registered. No Lead steps ticked.

- 2026-10-14 Builder (slice 3): admin cannot add or delete transactions (rows arrive via API;
  reject keeps the audit trail). Only quarantined rows are editable in the admin form. Approve
  re-runs the API validation on the stored fields, so a row also needs a `transaction_id`,
  `currency` and `category` before it can be approved; existing warnings are kept. Flag for Lead.

- 2026-10-14 Lead: commit `files/transaction_history.csv` as reference data (not imported by the app).

## Open questions for Lead
- README: add your own reasoning for choosing Django/Postgres (brief asks for the candidate's view);
  the README currently gives a neutral technical rationale.
- Brief asks for the AI-coding prompts used: export the Claude Code / Codex session prompts into
  `docs/prompts/` (agents can't reconstruct them faithfully).

## Deferred (next PRs)
- Review API; description-level category cache; async categorisation; CSV import.
- Labelled accuracy eval for the LLM categoriser (run in CI on prompt changes); few-shot examples
  if accuracy slips on real merchant text.
- Model-reported uncertainty (e.g. `uncertain` flag ⇒ review label) — needs a spec change.
- Tests the Tester listed as outstanding: expired JWT, OpenAPI contract, equal-timestamp ordering
  by creation time, Docker Compose smoke check.
- Local dev DB contains a `smoke` user created for the compose smoke test; remove when convenient.
