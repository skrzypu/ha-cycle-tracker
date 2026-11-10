---
id: BDR-0003
title: Cycle data lives in the user's own Google Sheet
status: proposed
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0004"]
---

# BDR-0003: Cycle data lives in the user's own Google Sheet

## Context

The product roadmap's Phase 3 envisioned an export to Google Drive, not a
canonical spreadsheet. The user direction now makes a Google Sheet the
canonical store, so that data entry does not depend on reaching Home Assistant.

## Decision

We will make it a product promise that cycle data lives in a Google Sheet owned
by the user, and that Home Assistant is a client.

A user can log a period from Home Assistant at home and edit the same sheet from
a phone outside the home network.

In scope: the user-owned sheet as the canonical store, with Home Assistant
reading and writing it. Out of scope: a separate mobile app, and any
project-hosted storage of cycle data.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Local-only storage | Data entry depends on reaching the Home Assistant instance. |
| One-way export | The user gets a copy, not an editable canonical store. |
| Separate mobile app | New app to build, ship, and maintain alongside the integration. |

## Expected impact

- **Users:** onboarding now requires a Google account, a Google Cloud project, a
  service account, and sharing the sheet with that service account. In exchange,
  data is user-owned, entry works from any phone with sheet access, and the data
  is available for spreadsheet analysis.
- **Revenue / cost:** no direct revenue. Cost is the support and documentation
  effort for Google Cloud setup. Estimates are unknown.
- **Operations / support:** support burden increases because configuration
  failures now include Google credentials, sharing, and sheet schema.
- **Risk / compliance:** Google can read the data, so the privacy disclosure
  must say so. There is no vendor lock-in beyond Google, but the product now
  depends on Google availability.

## Evidence

- `TempFiles/product_roadmap_ha_cycle_tracker.md`, Phase 3 — export to Google
  Drive, not a canonical spreadsheet; superseded by user direction.
- `README.md` — currently states the integration is fully local; the privacy
  section must change.
- User direction recorded in this decision.

Assumption: users who need phone access already have or can create a Google
account and a Google Cloud project. No user counts or support volumes are
available.

## Follow-up

- [ ] Write onboarding copy for the Google Cloud and service account setup.
- [ ] Add a privacy disclosure to the README stating that Google can read the
      data.
- [ ] Revisit this record if a non-Google canonical store is required.
