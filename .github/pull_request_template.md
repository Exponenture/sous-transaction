## What
<!-- One or two sentences. Link the task / ticket. -->

## Why
<!-- The problem this solves and the approach chosen (and what was rejected). -->

## Risk
<!-- Tenancy / auth, concurrency, money, performance, external calls. "Low" needs a reason. -->

## Tests
<!-- New/changed tests and what behaviour they pin. Who wrote them (human / Builder / Tester). -->

## Migration
<!-- None, or: what it does, is it reversible, safe on a live table (expand/contract)? -->

## Rollback
<!-- Revert the PR? Feature flag? Data to clean up? -->

## Checklist
- [ ] Querysets scoped to the caller's tenant; permissions explicit
- [ ] Writes that touch stock/money/state are atomic and race-safe
- [ ] Inputs validated; errors use the standard shape
- [ ] No N+1 (checked query count where it matters)
- [ ] `make test lint` green locally; CI green
