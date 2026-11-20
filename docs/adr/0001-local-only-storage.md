---
id: ADR-0001
title: Local-only data storage and processing
status: superseded
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: "ADR-0004"
related: []
---

# ADR-0001: Local-only data storage and processing

## Context

`README.md` states that Cycle Tracker is "Fully local: no cloud calls, no
external API, no telemetry". The `cycle-logging-services` specification
contains the requirement "Persist cycle data locally": all recorded cycle data
is stored in local Home Assistant storage and SHALL NOT be transmitted to any
external or cloud service.

The integration has no accounts, no authentication, and makes no network
calls. Period history and settings are written to Home Assistant's own storage
(`.storage/cycle_tracker_data`) and the manifest declares
`iot_class: local_polling`. The recorded rationale is limited to the stated
privacy promise and the specification requirement; no further rationale is
documented.

## Decision

We will store and process all cycle data locally in Home Assistant storage and
will make no cloud calls, external API calls, or telemetry.

Concretely: the integration has no external dependencies, no accounts, no
authentication, and no network requests. Persistence uses Home Assistant's
local storage only.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Cloud-hosted storage for cycle data | Contradicts the "fully local" promise in `README.md` and the "Persist cycle data locally" requirement; no backend exists. |
| External API for cycle prediction or statistics | Contradicts the "no external API" promise; prediction is calculated locally in pure Python. |
| Telemetry or analytics reporting | Contradicts the "no telemetry" promise in `README.md`. |

## Consequences

**Positive**

- Data exposure is limited to the Home Assistant instance.
- No third-party processor, account system, or vendor credential is involved.
- The integration works without internet access for its own operation.

**Negative / costs**

- No remote sync and no vendor backup.
- Multi-device or remote access is not supported by the integration; access is
  whatever the user's Home Assistant instance offers.
- Recovery depends on the user's Home Assistant backups.

**Risks and mitigations**

- Losing the Home Assistant instance or its backups loses the cycle history;
  there is no vendor-side recovery path. The mitigation is the user's own
  Home Assistant backup practice, not something the integration provides.

## Follow-up

- [ ] Record a new ADR before introducing any cloud storage, external API, or
      telemetry, and update the privacy section of `README.md` accordingly.
