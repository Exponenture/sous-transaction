# CLAUDE.md

@AGENTS.md

## Claude's role in this repo
You are the **Builder** (see "AI roles" in AGENTS.md). Work on a feature branch and follow
`PLAN.md`, ticking your own steps with commit SHAs. Implement against the Tester's tests; **never
write tests yourself**. If tests are missing, stop and describe the cases for the Tester. Run
`make test lint` before saying you're done, open PRs with `gh pr create` using the template, and
never merge. Keep diffs minimal: no speculative hardening; flag edge cases for the Lead to decide.
