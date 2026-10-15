# Plan: Transaction categorisation API

Spec: `NOTES.md` · Branch: `feat/transactions` → `fix/review-round-1` · PRs: [#1](https://github.com/Exponenture/sous-transaction/pull/1), [#2](https://github.com/Exponenture/sous-transaction/pull/2), [#3](https://github.com/Exponenture/sous-transaction/pull/3) (all merged)

**Status 2026-10-14:** build complete. PRs #1–#3 merged; `main` has the step-by-step history
(restored at `4cb5669`) plus the unit-suite PR (`2c583ee`). 289 tests, 97.05% coverage, CI green.
Remaining before submission: Lead ticks, repo public. See *Open questions for Lead*.

> History restored 2026-10-14: `main` was rebuilt from the branch commits (PR #1 and #2 had been
> squash-merged), so every SHA below is on `main`. Round-1 fixes first made on `feat/transactions`
> (`b6426b0`, `7ed791d`) are cited by their `main` equivalents.

Copy this file to `PLAN.md` at the start of a task. Tick a box only when its "done when" is true,
and append the commit SHA. Agents never tick **Lead** boxes.

## Roles
| Role | Who | Owns |
|---|---|---|
| Lead | Matt | Spec, cut line, approvals, triage of review findings, merge |
| Builder | Claude Code (own thread) | Plan + implementation; never writes tests |
| Tester | Codex (own thread) | All tests, black-box from `NOTES.md` |
| Reviewer | Codex (fresh thread) | Adversarial review via `docs/prompts/adversarial-review.md` |
| Gate | GitHub Actions | lint, tests + coverage report, migrations check, Docker Compose smoke (no type checker configured) |

## Steps
- [x] 1. Spec written in `NOTES.md` (problem, assumptions, model, endpoints, edge cases, cut line) — **Lead**
- [x] 2. Spec gap review; gaps resolved or labelled assumptions — Tester → **Lead**
- [x] 3. Contract tests written; suite is red for the right reason — Tester
  - Suites committed `59863b6`, `9bc7cbe`, `5733146`, `74fdcc8`, each red for the right reason when landed;
    unit suite + coverage `2c583ee` (PR #3). Tester to tick.
- [x] 4. Tests reviewed (do they pin the spec, not guesses?) — **Lead**
- [x] 5. Build plan approved (files, models, order of slices) — Builder → **Lead**
- [x] 6. Slice 1: model + migration + validation/quarantine service + 3 endpoints, rules categoriser only — green, diff read by Lead — Builder / **Lead**
  - Built `8c1f8a8`; `make test lint` green. Awaiting Lead diff read.
- [x] 7. Slice 2: LLM categoriser (Anthropic SDK, `backend/transactions/prompts/categorise.md`, timeout, fallback) — green, diff read by Lead — Builder / **Lead**
  - Built `59d4e2c`; full suite + live smoke test green. Awaiting Lead diff read.
- [x] 7a. Slice 3: admin review queue (filters, approve/reject actions) — green, diff read by Lead — Builder / **Lead**
  - Tests landed in `9bc7cbe` (they discover action names and the issue filter from the admin UI).
    Built `4d84b93`; `make test lint` green (all suites). Awaiting Lead diff read.
- [x] 7b. Slice 4: README — API docs, algorithm + prompts, trade-offs, why Django/Postgres — Builder / **Lead**
  - Written `640710d`; Lead's stack reasoning and exported prompts (`docs/prompts/`) added on PR #2. Awaiting Lead read.
- [x] 8. `make test lint` green; PR opened with template; CI green — Builder / Gate — `d884101`
  - PR #1: template, Backend check green at merge. PR #2: template; Backend, Docker Compose smoke and
    CodeRabbit green at `d884101` (258 tests).
- [x] 9. **Adversarial review** (fresh Codex thread); every finding triaged: fix · accept-with-reason · defer — Reviewer → **Lead**
  - Round 1 ran in the Tester's thread on a stale checkout (R1–R2 invalid), so it didn't count as
    independent. Round 2 ran in a fresh thread on PR #2 at `54f1976` (one attempt reviewed the wrong
    repo and was discarded); its two findings R10–R11 are fixed. All findings triaged, below.
    **Lead accepted round 2 as closing this step (2026-10-14); no round 3.**

  | # | Finding | Triage | Note |
  |---|---|---|---|
  | R1 | Admin registration absent (BLOCKER) | invalid (stale) | Built in `4d84b93`; 13/13 admin tests pass at HEAD |
  | R2 | README still scaffold | invalid (stale) | Written in `640710d` |
  | R3 | `"1e1000000"` amount → decimal.Overflow → 500 | **fixed** `0377e5c` | AM7(c); reproduced |
  | R4 | U+0000 anywhere in body → Postgres DataError → 500 | **fixed** `0377e5c` | AM6 policy; reproduced (unknown key and description) |
  | R5 | Rules put salary/transfer/refund under spending categories | **fixed** `0377e5c` | AM7(a); reproduced |
  | R6 | Anthropic constructor outside try → no fallback | **fixed** `0377e5c` | AM7(b); reproduced |
  | R7 | Concurrent identical first submissions can both call the AI | accept | One row stored; extra call costs < $0.001; preventing it means a DB lock held across a network call |
  | R8 | Admin reviewers see all owners' rows | accept / defer | Internal ops tool, staff + model permission; per-owner admin scoping deferred to multi-tenant work |
  | R9 | No endpoint-level explicit `permission_classes` | **fixed** `8c15792` | No behaviour change, covered by existing auth tests |
  | R10 | (round 2) NUL replacement can make keys collide; one value silently lost | **fixed** `9c57451` | AM8(a): 400, nothing stored; reproduced |
  | R11 | (round 2) Deep nesting (≥600) → RecursionError → 500 | **fixed** `9c57451` | AM8(b): > 32 levels → 400, iterative check; reproduced over HTTP. Bodies ~1000+ deep failed inside json.loads before our check, so a depth-safe parser maps RecursionError to the same 400 (checked to 100,000 levels) |
  | CI | Docker smoke job: first request reset (api reported ready before gunicorn listened) | **fixed** `bdecc3d` | api healthcheck; verified CI-style locally |
- [x] 10. PR walked by risk, squash-merged, `PLAN.md` deferred list copied to the next task — **Lead**
  - PRs #1–#3 merged. For this task `main` keeps per-step commits instead of squashes (the brief scores
    commit history); see the history-restore decision.

## Decisions (append as you go)
- 2026-10-14 Scope: single-transaction API only; no CSV import, no batching (Lead). CSV import was
  skipped on the SOUS reviewer's instruction, confirmed by the Lead 2026-10-14; README says so up front.
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
  Already implemented in `8c1f8a8`; covered since `5733146` (`test_wrong_json_types_are_flagged_without_coercion`).
- 2026-10-14 Tester: added lightweight admin review HTTP contracts in
  `backend/tests/test_transaction_admin.py`; lint passes, tests are red because
  transaction admin URLs are not registered. No Lead steps ticked. (Resolved: admin built `4d84b93`, 13/13 pass.)
- 2026-10-14 Builder (slice 3): admin cannot add or delete transactions (rows arrive via API;
  reject keeps the audit trail). Only quarantined rows are editable in the admin form. Approve
  re-runs the API validation on the stored fields, so a row also needs a `transaction_id`,
  `currency` and `category` before it can be approved; existing warnings are kept. **Confirmed by
  Lead 2026-10-14.**
- 2026-10-14 Lead: commit `files/transaction_history.csv` as reference data (not imported by the app).
- 2026-10-14 Lead: review round 1 triage as in step 9; NUL policy = replace U+0000 with U+FFFD on
  receipt + blocking `unsupported_character` (NOTES AM6); review fixes pinned as NOTES AM7, which
  also carries the wrong-JSON-type decision so the Tester sees it in the spec.
- 2026-10-14 Tester: added AM6/AM7 adversarial-review regressions, expired JWT,
  creation-order and OpenAPI contracts; Docker smoke jobs use two synthetic rows.
  Twelve regression cases currently fail for the reproduced bugs; twelve pass.
  Concurrent AI-call and admin ownership policies remain unpinned. (Resolved in triage: R7 accepted,
  R8 deferred; neither needs a test.)
- 2026-10-14 Lead: PR #1 squash-merged at `2d0bb01` (then main `1000ff1`), before step 9 and before the
  round-1 fixes. The 7 later commits were replayed unchanged onto `fix/review-round-1` → PR #2.
  PR #2 was squash-merged too (`ac1444a`). History then restored on `main` from the branches (see top),
  where R3–R6 are `0377e5c`, R9 `8c15792`, tests `5733146`.
- 2026-10-14 Lead: review round 2 (fresh thread, correct repo) found R10–R11; policy = NOTES AM8
  (reject with 400 what can't be stored faithfully: key collisions after NUL replacement, nesting
  > 32 levels). Lossless alternative (extra raw-text column) rejected: migration + breaks AM6
  replay rule for an attacker-only case.
- 2026-10-14 Builder: AM8 implemented. Tester to add one case: a body nested ~2000+ levels (fails in
  the JSON parser, not our check) also returns 400 `validation_error`; verified manually only.
- 2026-10-14 Tester: added 15 AM8 contracts in `test_transaction_unstorable_bodies.py`;
  4 pass and 11 fail for the pending collision/depth fixes. Small synthetic
  fixtures only; no application code or Lead checklist steps changed. (Resolved: all pass after `9c57451`.)
- 2026-10-14 Lead: README stack reasoning = chosen to match SOUS's stack (OfferZen profile), not the
  Lead's native stack, so some latitude asked for in a code walk-through. Builder exported all
  prompts to `docs/prompts/` (Builder-session prompts verbatim from the session export).
- 2026-10-14 Lead: confirmed the slice 3 admin choices: (1) no add or delete in the admin (rows
  arrive via the API; reject keeps the audit trail); (2) only quarantined rows are editable;
  (3) approve re-runs API validation, so `transaction_id`, `currency` and `category` are required.
  Superuser delete and audited edits of categorised rows stay possible later as deliberate features.
- 2026-10-14 Lead: accepted review round 2 as closing step 9; no round 3. Merge of PR #2 is the Lead's.
- 2026-10-14 Lead: restore granular commit history on `main` (brief scores "small and logical
  commits"). Builder rebuilt it on `history/main` (scaffold → slice commits → PR #2 commits → CSV
  note), tree verified identical to `main` + the CSV note; the Lead force-pushes it to `main`.

- 2026-10-14 Tester: added 31 pure-function unit cases without HTTP/database access;
  pytest-cov measures statement and branch coverage for core/transactions, with
  reports retained by CI and scoped measured figures documented in README.
- 2026-10-14 Lead: `main` force-pushed to the restored history (`4cb5669`); PR #3 (unit suite +
  coverage) merged as `2c583ee`. Builder re-measured: 289 tests pass, coverage 97.05% combined
  (97.38% statements, 95.71% branches) across `core` and `transactions`.

- 2026-10-14 Lead: Codex-side prompts will not be exported; `docs/prompts/` notes this. The
  Builder-drafted handoffs, spec and standing files are the substantive Codex instructions.

- 2026-10-14 Lead: four out-of-scope architecture items discussed with the SOUS interviewer are
  recorded under *Future architecture* (async enrichment, learned mappings, queue + retries,
  evals + observability) and in the README. They replace the narrower deferred items for a category
  cache, async categorisation and an accuracy eval.

## Open questions for Lead
- Tick Lead steps 1, 2, 4, 5, 6, 7, 7a, 7b, 9, 10 once satisfied; Tester to tick 3.
- Make the repo public (history and published files scanned: no secrets, no tracked `.env`).

## Future architecture (out of scope; discussed with the SOUS interviewer)
Recorded 2026-10-14 by the Lead as the next architectural steps; detail in README "Future architecture".
1. **Fast acknowledgement, async enrichment:** POST stores/quarantines and returns at once with
   `categorisation_status: "pending"`; categorisation runs as a job queued in `on_commit`. Callers
   like a Stripe webhook never wait on the AI or hold the connection open.
2. **Learned category mappings:** a `CategoryMapping` table on a normalised description, checked
   before the AI. The AI is only called on a missing mapping, every answer is saved, and reviewer
   corrections override. Lookup order: known mapping, AI, keyword rules.
3. **Queue + retries:** idempotent jobs keyed by transaction id; exponential backoff with jitter on
   timeouts/429/5xx; rules fallback and dead-letter after the last attempt; provider rate limiting.
4. **Evals + observability:** labelled eval set run in CI on prompt/model/rules changes; metrics for
   AI latency/errors/fallbacks, mapping hit rate, cost, queue depth, quarantine and review-queue
   age; OpenTelemetry tracing and alerts.

- 2026-10-15 Tester: added four admin action authorization contracts on
  `fix/admin-action-permissions`. View-only staff must neither see nor execute
  approve/reject; crafted POSTs must preserve status, issues, raw input, review
  metadata and update time. Change-only staff positive controls pass. Targeted
  run: 15 passed, 2 failed, reproducing the authorization bug; no application
  code changed and no Lead checklist steps ticked.

## Deferred (next PRs)
- Per-owner scoping in the admin (review R8).
- Review API; CSV import (skipped at the SOUS reviewer's request).
- 404 responses use error code `"error"` (and an empty message for a malformed id) instead of
  `"not_found"`; comes from `core/exceptions.py` in the scaffold. Small fix + Tester case.
- Few-shot examples in the prompt if accuracy slips on real merchant text (measure with the evals below).
- Model-reported uncertainty (e.g. `uncertain` flag ⇒ review label) — needs a spec change.
- Tester: one case for a body nested ~2000+ levels (JSON-parser path of AM8b) returning 400.
- Local Docker dev DB has `smoke` and `smoke2` users (random, unsaved passwords) from manual
  end-to-end checks, and a local `admin` superuser whose login is only in the gitignored `.env`.
- Remote branch `docs/csv-scope` is redundant (its commit is on `main`); safe to delete. Keep
  `feat/transactions` and `fix/review-round-1`: their SHAs are cited above.
