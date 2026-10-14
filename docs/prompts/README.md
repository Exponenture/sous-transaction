# Prompts

## Categorisation prompt (used by the application)

The prompt the API sends to Claude to categorise each transaction:
[`backend/transactions/prompts/categorise.md`](../../backend/transactions/prompts/categorise.md).
It ships with the code because the Docker image is built from `backend/`. The README's
[Categorisation prompt](../../README.md#categorisation-prompt) section shows it in full, with the
user message format and the response schema that restricts answers to the 10 categories.

## Prompts used to build the project (AI coding tools)

How the agents split the work is in the root README ("How AI tools were used") and
[`AGENTS.md`](../../AGENTS.md).

| File | What it is |
|---|---|
| [`builder-session.md`](builder-session.md) | Every prompt the Lead typed into the Claude Code Builder session, verbatim and in order |
| [`codex-handoffs.md`](codex-handoffs.md) | Prompts the Builder drafted for the Tester and Reviewer (Codex) |
| [`adversarial-review.md`](adversarial-review.md) | The Reviewer's standing prompt |
| [`codex-test-plan.md`](codex-test-plan.md) | The Tester's proposed test plan, reviewed before any tests were written |
| [`reviews/`](reviews/) | Codex adversarial review output, rounds 1 and 2 (triage in `PLAN.md` step 9) |

The Lead's own messages inside the Codex threads were not exported; the substantive instructions
Codex received are the handoffs above plus the spec and standing files below.

Standing instructions every agent read: [`AGENTS.md`](../../AGENTS.md) (engineering rules and roles),
[`CLAUDE.md`](../../CLAUDE.md) (Builder role), and the spec [`NOTES.md`](../../NOTES.md).
