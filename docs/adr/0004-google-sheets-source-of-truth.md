---
id: ADR-0004
title: Google Sheets is the source of truth for cycle data
status: accepted
date: 2026-11-09
deciders: []
supersedes: "ADR-0001"
superseded-by: null
related: ["BDR-0003"]
---

# ADR-0004: Google Sheets is the source of truth for cycle data

> **Status note:** accepted on 2026-11-20. When proposed, acceptance waited for
> the domain data model to be settled; that precondition was met by ADR-0006
> (accepted 2026-11-10). With acceptance this decision takes effect and
> supersedes ADR-0001.

## Context

The user wants to enter data from a phone outside the Home Assistant network,
see and analyze the data in a spreadsheet, and own the storage. ADR-0001
(local-only storage, no cloud, no external API) no longer matches those needs.

Home Assistant core `google_sheets` was evaluated and rejected: it only accesses
the spreadsheet it creates during setup and can only append rows, so it cannot
update an existing period row. An Apps Script webhook was rejected because it
requires a public endpoint and a shared secret. OAuth2 was rejected because the
`spreadsheets` scope covers all of the user's spreadsheets and refresh tokens
expire after 7 days while the app is in Testing.

## Decision

We will use a Google Sheet owned by the user as the single source of truth for
period records. The integration reads and writes the sheet through the Google
Sheets API using a service account JSON key.

The sheet has one row per period with these columns, in this order:

| Column | Meaning |
|---|---|
| `period_id` | Stable identifier for the period row |
| `start_date` | Inclusive period start date |
| `end_date` | Inclusive period end date; empty while the period is open |
| `flow_intensity` | `spotting`, `light`, `medium`, or `heavy` |
| `notes` | Free-text notes |
| `updated_at` | Timestamp of the last write to the row |
| `source` | Origin of the row |

Home Assistant storage keeps only a last-known-good cache and sync metadata.
`log_start` appends a row. `log_end` updates the latest row whose `end_date` is
empty. Manual edits in the sheet are picked up on the next poll, and deleting a
row deletes the period. When the sheet or credentials are missing, the
integration raises a repair issue with setup instructions instead of writing
locally.

In scope: period records and the logging services. Out of scope: storing other
tracked metrics in the sheet, and any local write fallback.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Stay local-only | No data entry from a phone outside the Home Assistant network. |
| One-way export to Sheets | A copy is not a source of truth; edits do not flow back. |
| Home Assistant core `google_sheets` | Append-only and limited to the document it creates; cannot update a period row. |
| Apps Script webhook | Public endpoint and a shared secret to protect. |
| OAuth2 | Broad `spreadsheets` scope and 7-day refresh-token expiry in Testing. |
| Encrypted Google Drive backup only | Backs up data but does not allow editing a sheet. |

## Consequences

**Positive**

- Period data can be entered from any device with access to the sheet.
- The user owns and can analyze the data in a spreadsheet.
- Home Assistant remains a client rather than the only place the data exists.

**Negative / costs**

- Google can read the data, which is special-category health data under GDPR
  Article 9.
- The service account key is stored in Home Assistant configuration and
  therefore in backups. Backups are encrypted by default, and the key grants
  access only to the shared sheet.
- Google availability and the network become dependencies, and polling adds
  latency.
- The column schema becomes a contract.
- Concurrent edits resolve last-write-wins.
- The integration must validate rows and raise repair issues.
- Key rotation is manual, and there is no local write fallback.

**Risks and mitigations**

- Sheet corruption or schema drift: validate rows on read and surface repair
  issues.
- Credential leakage: keep the key out of the repository, scope access to the
  shared sheet, and document rotation.
- Divergent edits: accept last-write-wins and stamp `updated_at` on every
  write.

## Follow-up

- [ ] Implement the sheet configuration step and the repair issues.
- [ ] Document service account key rotation.
- [ ] Decide the polling interval and whether a Google Form is supported.
