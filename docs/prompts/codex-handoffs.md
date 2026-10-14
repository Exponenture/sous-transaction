# Builder → Codex handoff prompts

The Builder (Claude Code) never writes tests or reviews its own work. When a step needed the Tester
or Reviewer (Codex, separate threads), the Builder drafted the prompt below and the Lead passed it
on. Verbatim from the Builder session (times UTC, 2026-10-14). Commit IDs inside the prompts are as they were at the
time; after the history restore on `main`, `d0c5c46` is `54f1976` and `826b203` is `4997d6f`. The Lead's own Codex sessions may
have added context; those prompts are in [`codex-sessions/`](codex-sessions/) when exported.

## 15:27 — Tester: regressions for review round 1 (NOTES AM6/AM7)

> Read NOTES.md AM6 and AM7 on `feat/transactions` (pull first). Add failing tests for:
> - **NUL characters:** NUL in a known field, an unknown key, a nested value and a key name each becomes `U+FFFD` in `raw_payload`, plus one blocking `unsupported_character` per affected top-level key. Resending the same NUL payload returns 200.
> - **Extreme amounts:** values like `"1e1000000"` and `"-1e-1000000"` get `invalid_amount` instead of a 500.
> - **Rule precedence:** the three AM7(a) examples come out as Miscellaneous, and the AM2 table still passes.
> - **AI client failure:** the `Anthropic` constructor raising leads to the rules fallback with a `categorisation_fallback` warning.
> - **Wrong JSON types:** per AM7(d).

Result: `test_transaction_review_regressions.py` and the Docker smoke job.

## 15:42 — Reviewer: fresh-thread adversarial review of PR #2

Prefixed to [`adversarial-review.md`](adversarial-review.md):

> Work in `/Users/Matt/Dev/sous-transactions`. Run `git fetch origin && git checkout fix/review-round-1 && git pull`, then confirm `git log -1` shows `d0c5c46`. Review `git diff origin/main...HEAD` against `AGENTS.md` and `NOTES.md` (including AM6/AM7), following `docs/prompts/adversarial-review.md`. Do not modify files.

The commit check was added after round 1 reviewed a stale checkout and a later attempt reviewed the
wrong repository. Result: [`reviews/round-2.md`](reviews/round-2.md).

## 15:50 — Tester: unstorable bodies (NOTES AM8)

> Pull `fix/review-round-1` (should be at `826b203`). Read NOTES.md AM8 and add failing tests:
> - **(a) Key collisions:** top-level and nested keys that collide after `U+0000` → `U+FFFD` replacement get a 400 `validation_error`, nothing is stored (`?status=all` count stays 0), and the AI is never called.
> - **(b) Depth limit:** nesting at exactly 32 levels is accepted; 33 levels, and something extreme like 2000, gets a 400 with nothing stored. Cover both arrays and objects.
> - **Resends:** a colliding payload sent twice is 400 both times.

Result: `test_transaction_unstorable_bodies.py` (the ~2000-level case is still to add; see `PLAN.md`).
