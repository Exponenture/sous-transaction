# NOTES — Transaction categorisation (spec)

Status: **Approved by Lead 2026-10-14.** Source brief: SOUS Senior Engineer Assessment.

## Problem
Accept single banking transactions over an API, assign each one of 10 fixed categories using AI,
and serve them back. Input is assumed **dirty**: anything that doesn't add up logically is
accepted, stored, **quarantined** and labelled with machine-readable issues for human review —
never silently fixed, never silently dropped.

## Scope
- In: `POST /api/transactions/`, `GET /api/transactions/`, `GET /api/transactions/{id}/`;
  validation + quarantine; AI categorisation with rules fallback; admin review queue; docs.
- Out: CSV import (the SOUS reviewer asked for it to be skipped), batch submission, editing/deleting via the API, a review API, multi-currency
  conversion. `files/transaction_history.csv` is used only as a reference for realistic and dirty data.

## Assumptions (labelled)
- A1. Timestamps without an offset are local time in **Europe/Amsterdam** (setting `TIME_ZONE`).
  Timestamps with an explicit offset are taken as given.
- A2. Currency is optional on input and defaults to `EUR`.
- A3. Sign convention: **debit = money out = negative amount; credit = money in = positive amount.**
- A4. Auth stays JWT (scaffold default). Transactions belong to the authenticated caller; callers
  only ever see their own (other users' rows return 404, never 403).
- A5. `transaction_id` is the client's idempotency key, unique **per owner**.
- A6. Money movements with no spending meaning (transfers, salary, tax refunds, ATM withdrawals)
  categorise as `Miscellaneous`. That is correct under the brief, not an error.

## Categories (exactly these 10, stored as these strings)
`Groceries`, `Dining Out`, `Utilities`, `Transportation`, `Entertainment`, `Healthcare`,
`Shopping`, `Housing`, `Education`, `Miscellaneous`.

## Data model — `Transaction`
| field | type | notes |
|---|---|---|
| `id` | UUID | PK, server-generated; used in `/transactions/{id}/` |
| `owner` | FK user, `on_delete=PROTECT` | caller |
| `transaction_id` | str ≤ 64, nullable | client id; `UniqueConstraint(owner, transaction_id)` |
| `amount` | Decimal(14,2), nullable | null only when quarantined |
| `currency` | char(3) | default `EUR` |
| `timestamp` | aware datetime, nullable | null only when quarantined |
| `description` | str ≤ 255, nullable | |
| `transaction_type` | `debit` \| `credit`, nullable | |
| `account_number` | str ≤ 34, nullable | normalised (uppercase, no spaces); PII — never logged |
| `category` | one of the 10, nullable | null only if description unusable |
| `categorisation_source` | `llm` \| `rules` \| `none` | |
| `status` | `categorised` \| `quarantined` \| `rejected` | |
| `issues` | JSON list | `[{code, field, severity, message}]`, `[]` when clean |
| `raw_payload` | JSON | the request body exactly as received |
| `created_at` / `reviewed_at` | aware datetime | `reviewed_by` FK user, nullable |

DB `CheckConstraint`s: `status='categorised'` ⇒ amount, timestamp, description, transaction_type,
account_number, category all NOT NULL; `category` ∈ the 10; `transaction_type` ∈ {debit, credit};
`status` ∈ the 3 values. Indexes: `(owner, status, timestamp)`.

## Input (POST body, JSON object)
`transaction_id`, `amount`, `timestamp`, `description`, `transaction_type`, `account_number`,
optional `currency`. Unknown keys are ignored (kept in `raw_payload`). Amount may be a JSON number
or a numeric string. Strings are trimmed; `transaction_type` and `currency` are case-insensitive.

## Validation → issues
**Blocking** (any one ⇒ `status=quarantined`):
| code | when |
|---|---|
| `missing_field` | a required field is absent, null or blank after trimming (one issue per field) |
| `invalid_amount` | not a finite decimal, more than 2 decimal places, or abs ≥ 10^12 |
| `zero_amount` | amount is 0 |
| `invalid_timestamp` | not parseable as ISO 8601 (`YYYY-MM-DD HH:MM:SS[.ffffff][offset]` or `T` separator) |
| `future_timestamp` | more than 5 minutes after server now |
| `nonexistent_local_time` | naive local time falls in the DST spring-forward gap |
| `invalid_transaction_type` | not `debit`/`credit` |
| `sign_type_mismatch` | debit with positive amount, or credit with negative amount |
| `invalid_currency` | not 3 letters |
| `invalid_account_number` | after normalising, not 2 letters followed by 8–32 alphanumerics |
| `invalid_description` | longer than 255 chars |
| `invalid_transaction_id` | not a string/integer, or longer than 64 chars |

**Warning** (row stays `categorised`, issue recorded):
| code | when |
|---|---|
| `ambiguous_local_time` | naive local time falls in the DST fall-back hour; first occurrence assumed |
| `categorisation_fallback` | AI categoriser failed or was unavailable; rules used |

Every rule is evaluated (issues accumulate; validation doesn't stop at the first failure). Fields
that fail to parse are stored as null; fields that parse are stored even on quarantined rows.

## Categorisation
- Runs for every row with a usable description, **including quarantined rows** (gives the reviewer
  a suggestion).
- Primary: Claude (`claude-haiku-5-5`) via structured output constrained to the 10 categories.
  Input sent: description, amount, transaction type — **never** account number or owner.
  Timeout 5 s, no retries in the request path. Prompt lives in `docs/prompts/categorise.md`.
- Fallback: deterministic keyword rules (`categorisation_source=rules`, warning
  `categorisation_fallback`). No API key configured ⇒ rules, same warning. No keyword match ⇒
  `Miscellaneous`.
- Any LLM answer outside the 10 categories counts as a failure ⇒ fallback.

## Endpoints (all require JWT; errors use the standard `{"error": {...}}` envelope)
**`POST /api/transactions/`**
- 201 + transaction body: new row (either `categorised` or `quarantined` — the body says which).
- 200 + original body: replay — same owner, same `transaction_id`, identical payload.
- 409 `conflict`: same owner + `transaction_id`, different payload. Nothing is stored.
- 400 `validation_error`: body isn't a JSON object. (The only 400 — dirty data is quarantined, not rejected.)
- 401: no or bad token.
- A row with a missing or invalid `transaction_id` is quarantined and gets no replay protection.

**`GET /api/transactions/`** — caller's rows, paginated (20), newest `timestamp` first (nulls last,
then `created_at` desc). Default `status=categorised` (the brief's "categorised transactions");
`?status=quarantined|rejected|all`; `?category=<one of 10>`. Invalid filter value ⇒ 400.

**`GET /api/transactions/{id}/`** — any status. 404 if missing, malformed UUID, or owned by someone else.

**Response body**: `id, transaction_id, amount (string, 2 dp), currency, timestamp (ISO 8601 with
offset), description, transaction_type, account_number, category, categorisation_source, status,
issues, created_at`. `raw_payload` is included on the detail endpoint only.

## Human review (Django admin)
Admin list filtered by status/issue code, showing issues. Actions: **approve** (re-validate the
edited row; allowed only with no blocking issues ⇒ `categorised`, sets `reviewed_by/at`) and
**reject** (⇒ `rejected`). `raw_payload` is read-only.

## Edge cases to pin in tests
Sign mismatch both ways; amount as string `"-12.50"` vs number; `"1e3"`; `"NaN"`; 3 dp; zero;
naive vs offset timestamps; DST gap (2024-03-31 02:30) and overlap (2024-10-27 02:30); future
timestamp; `DEBIT ` with case/space; account number with spaces/lowercase; empty JSON object
(every field missing); JSON array body; replay identical vs conflicting; same `transaction_id` for
two different owners; LLM returns an off-list category; LLM times out; no API key.

## Amendments (Lead-approved 2026-10-14, after test-plan review)
**AM1. LLM seam.** Categorisation lives in `transactions/categorisation.py`. The LLM path builds
`anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=5, max_retries=0)` (module-level
import `anthropic` in that file) and calls `client.messages.create(...)` once per categorisation.
Tests mock `transactions.categorisation.anthropic.Anthropic`. Empty `ANTHROPIC_API_KEY` ⇒ the
client is never constructed; rules are used with `categorisation_fallback`. Raised exceptions,
timeouts, malformed responses and off-list categories are all failures ⇒ fallback.

**AM2. Rules contract.** Case-insensitive, whole-word keyword matching. The keyword list is an
implementation detail; this mapping of the sample descriptions is the contract:
| description | category |
|---|---|
| Albert Heijn Purchase, AH Online Groceries | Groceries |
| NS Train Ticket, Car Lease Payment | Transportation |
| Eneco Energy Bill, Payment to Ziggo, T-Mobile Bill Payment, Municipal Tax Payment | Utilities |
| Netflix Subscription | Entertainment |
| Bol.com Purchase | Shopping |
| Rent Payment | Housing |
| Tax Refund, Salary from Employer, Transfer to ING Account, Bunq Transfer, PayPal Transfer, Payment to Rabobank, Payment to Credit Card, iDEAL Payment, Geldmaat ATM Withdrawal | Miscellaneous |
| anything with no keyword match | Miscellaneous |
No sample description maps to Dining Out, Healthcare or Education; rules for those exist but are not pinned.

**AM3. Identical replay.** Two payloads are identical when the parsed JSON objects are equal
(key order irrelevant; JSON numbers compared by value, so `12.5` == `12.50`; a string never equals
a number, so `"12.50"` ≠ `12.5`; an extra or missing key — including unknown keys — is a difference).
Replay of a row in any status returns it with 200.

**AM4. Admin approve.** Allowed on `quarantined` rows only. Recomputes `issues` from the stored
(reviewer-edited) field values, not from `raw_payload`. No blocking issues ⇒ `categorised`,
warnings kept, `reviewed_by/at` set; otherwise the row stays quarantined with the recomputed issues
and the admin shows an error. The reviewer may set `category` directly; approve never calls the
LLM. Reject is allowed on `quarantined` rows only ⇒ `rejected`, `reviewed_by/at` set.

**AM5. Added cases.** Non-object body (array, scalar, malformed JSON) ⇒ 400, nothing stored.
PUT/PATCH/DELETE on both routes ⇒ 405. Issue shape is exactly `{code, field, severity, message}`
with `severity` ∈ {`blocking`, `warning`} and `field` null when not field-specific. Account number
never appears in log output (check with `caplog` on clean and dirty submissions). The future-
timestamp boundary is tested relative to now (now+4 min clean, now+6 min quarantined); no
time-freezing dependency.

**AM6. NUL characters (Lead-approved 2026-10-14, after adversarial review).** PostgreSQL cannot
store U+0000 in text or JSONB. On receipt, before validation, replay matching or storage, every
U+0000 in the body (object keys and string values, at any depth) is replaced with U+FFFD. The
sanitised body is what `raw_payload` stores and what replay equality (AM3) compares, so resending
the same NUL-containing payload is an identical replay (200). Each top-level key whose name or
value (at any depth) contained U+0000 gets one blocking issue `unsupported_character`, with `field`
= that key as sanitised. The row is quarantined; it is never a 500.

**AM7. Review fixes (Lead-approved 2026-10-14).** (a) Rules precedence: money-movement keywords
(salary, transfer, refund, ATM, withdrawal, credit card) are checked before spending keywords and
map to `Miscellaneous`, e.g. "Salary from School Employer", "Transfer to Rent Account" and
"Tax Refund Netflix" are all `Miscellaneous`. The AM2 table is unchanged. (b) AM1 failures include
the `anthropic.Anthropic(...)` constructor raising: fall back to rules with
`categorisation_fallback`. (c) Any amount whose decimal arithmetic fails (e.g. `"1e1000000"`) is
`invalid_amount`, never a 500. (d) A field sent as the wrong JSON type (e.g. `"description": 123`,
`"timestamp": 1700000000`, `"amount": true`) gets that field's `invalid_*` code; nothing is coerced
(`transaction_id` may still be a string or integer).

**AM8. Bodies that cannot be stored faithfully (Lead-approved 2026-10-14, review round 2).**
Quarantine means storing the input, so input that can't be stored faithfully is rejected instead:
**400 `validation_error`, nothing stored, no AI call**, checked before validation and replay
matching. (a) Two keys in the same object (at any depth) that become identical after AM6's
U+0000 → U+FFFD replacement, e.g. `{"extra\u0000": 1, "extra\ufffd": 2}`. (b) JSON nesting deeper
than 32 levels (the top-level object is level 1; each nested object or array adds one), checked
without recursion. Neither occurs in real bank transactions; both are narrow, documented
exceptions to "quarantine, never reject", alongside "body isn't a JSON object" (AM5).

## Cut line
Must: model + validation/quarantine + 3 endpoints + rules categoriser + LLM categoriser + docs.
Should: admin approve/reject actions. Deferred: review API, description-level category cache,
async categorisation, CSV import.
