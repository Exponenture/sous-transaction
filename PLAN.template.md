# Plan: <task name>

Spec: `NOTES.md` · Branch: `feat/<slug>` · PR: #<n>
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
- [ ] 6. Slice 1: <name> — green, diff read by Lead — Builder / **Lead**
- [ ] 7. Slice 2: <name> — green, diff read by Lead — Builder / **Lead**
- [ ] 8. `make test lint` green; PR opened with template; CI green — Builder / Gate
- [ ] 9. **Adversarial review** (fresh Codex thread); every finding triaged: fix · accept-with-reason · defer — Reviewer → **Lead**
- [ ] 10. PR walked by risk, squash-merged, `PLAN.md` deferred list copied to the next task — **Lead**

## Decisions (append as you go)
- 

## Deferred (next PRs)
- 
