# Plan: Transaction categorisation API

Spec: `NOTES.md` · Branch: `feat/transactions` · PR: (not opened)
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
- [ ] 7. Slice 2: LLM categoriser (Anthropic SDK, `docs/prompts/categorise.md`, timeout, fallback) — green, diff read by Lead — Builder / **Lead**
- [ ] 7a. Slice 3: admin review queue (filters, approve/reject actions) — green, diff read by Lead — Builder / **Lead**
- [ ] 7b. Slice 4: README — API docs, algorithm + prompts, trade-offs, why Django/Postgres — Builder / **Lead**
- [ ] 8. `make test lint` green; PR opened with template; CI green — Builder / Gate
- [ ] 9. **Adversarial review** (fresh Codex thread); every finding triaged: fix · accept-with-reason · defer — Reviewer → **Lead**
- [ ] 10. PR walked by risk, squash-merged, `PLAN.md` deferred list copied to the next task — **Lead**

## Decisions (append as you go)
- 2026-10-14 Scope: single-transaction API only; no CSV import, no batching (Lead).
- 2026-10-14 Dirty input is accepted and quarantined with labelled issues, not rejected with 400 (Lead).
- 2026-10-14 Logically impossible rows (e.g. sign/type mismatch, ~49% of sample CSV) are blocking (Lead).
- 2026-10-14 Naive timestamps = Europe/Amsterdam local time (Lead).
- 2026-10-14 Spec amendments AM1–AM5 after test-plan review: LLM mock seam, rules mapping, replay equality, admin approve semantics, added cases (Lead).

- 2026-10-14 Tester: added black-box submission/retrieval/integrity contract tests under
  `backend/tests/`; coverage, explicit assumptions and remaining slice tests are in
  `docs/testing/transactions.md`. No Lead steps ticked. Step 3 remains unticked until
  the tests have a commit SHA and outstanding contract decisions are reviewed.

- 2026-10-14 Tester: checked NOTES.md amendments AM1–AM5 and added AI, rules,
  replay-equality and HTTP/logging edge tests; replaced fixed-clock future tests
  with relative-time tests. Admin review coverage remains outstanding.
- 2026-10-14 Builder: runtime prompt lives at `backend/transactions/prompts/categorise.md`, not
  `docs/prompts/` as NOTES says — the Docker build context is `backend/`, so docs/ is not in the image.
  `docs/prompts/` keeps the AI-coding-tool prompts; README will link both. Needs Lead OK.
- 2026-10-14 Builder: LLM call uses `claude-haiku-5-5` with thinking disabled and a JSON-schema
  enum of the 10 categories (`output_config.format`). Live smoke test on the 20 sample
  descriptions + 2 extras + 1 prompt-injection string: 23/23 matched the rules table, 1.1–2.8 s each.
- 2026-10-14 Builder: wrong JSON types (e.g. numeric description) map to that field's `invalid_*`
  code; `transaction_type` widened to 16 chars so the CHECK constraint (not varchar length) rejects bad values.

## Deferred (next PRs)
- Review API; description-level category cache; async categorisation; CSV import.
