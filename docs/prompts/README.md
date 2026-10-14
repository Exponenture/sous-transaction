# Prompts

Every prompt used to build this project, as the brief asks. How the agents split the work is in
the root README ("How AI tools were used") and [`AGENTS.md`](../../AGENTS.md).

| File | What it is |
|---|---|
| [`builder-session.md`](builder-session.md) | Every prompt the Lead typed into the Claude Code Builder session, verbatim and in order |
| [`codex-handoffs.md`](codex-handoffs.md) | Prompts the Builder drafted for the Tester and Reviewer (Codex) |
| [`adversarial-review.md`](adversarial-review.md) | The Reviewer's standing prompt |
| [`codex-test-plan.md`](codex-test-plan.md) | The Tester's proposed test plan, reviewed before any tests were written |
| [`reviews/`](reviews/) | Codex adversarial review output, rounds 1 and 2 (triage in `PLAN.md` step 9) |
| [`codex-sessions/`](codex-sessions/) | The Lead's prompts in the Codex Tester/Reviewer threads (exported from Codex) |

Standing instructions every agent read: [`AGENTS.md`](../../AGENTS.md) (engineering rules and roles),
[`CLAUDE.md`](../../CLAUDE.md) (Builder role), and the spec [`NOTES.md`](../../NOTES.md).

The prompt the **application** sends to Claude at runtime is not here: it ships with the code at
[`backend/transactions/prompts/categorise.md`](../../backend/transactions/prompts/categorise.md)
(the Docker image is built from `backend/`).
