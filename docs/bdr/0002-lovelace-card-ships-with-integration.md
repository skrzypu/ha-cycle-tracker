---
id: BDR-0002
title: Lovelace card ships inside the integration repository
status: accepted
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: ["BDR-0001"]
---

# BDR-0002: Lovelace card ships inside the integration repository

## Context

The product roadmap makes a dedicated Lovelace card part of Phase 1: a card for
one-tap logging of period start and end. The archived
`python-only-hacs-readiness` change explicitly listed the Lovelace card as a
non-goal, so the repository currently has no UI assets.

Cycle Tracker is distributed from GitHub as a single HACS custom repository,
and the project wants to keep one HACS entry. A card is a UI asset that must be
versioned and delivered together with the integration it talks to.

## Decision

We will ship the Lovelace card inside the integration repository at
`custom_components/cycle_tracker/www/cycle-tracker-card.js`, distributed through
the existing HACS Integration entry.

The integration registers the static path and the Lovelace resource during
setup, so users do not add the card as a separate HACS Dashboard repository.

In scope: the card source and its registration by the integration. Out of
scope: a separate card repository, a second HACS entry, and independent card
versioning.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Separate repository `ha-cycle-tracker-card` | Independent versioning, but two repositories, two release processes, and version coordination between card and integration. |
| Two HACS entries in the same repository | HACS may reject the duplicate entry. |
| No card, services only | Worse user experience for the one-tap logging flow the roadmap calls for. |

## Expected impact

- **Users:** one HACS installation delivers both the integration and the card;
  updates arrive with the integration. The card is not a separate HACS
  Dashboard entry.
- **Revenue / cost:** no direct revenue. Release overhead stays at one release
  per version.
- **Operations / support:** one release and one version number; the card
  version always matches the integration.
- **Risk / compliance:** the card is served from the integration's own static
  path; no additional distribution channel or catalog entry is introduced.

## Evidence

- `TempFiles/product_roadmap_ha_cycle_tracker.md`, Phase 1 — lists a dedicated
  Lovelace card for one-tap logging.
- `openspec/changes/archive/2026-11-05-python-only-hacs-readiness/design.md`,
  Non-Goals — explicitly excludes the Lovelace card from that change.
- Repository inspection — no UI assets exist yet under
  `custom_components/cycle_tracker/`.
- `docs/bdr/0001-hacs-custom-repository-distribution.md` — single HACS
  custom-repository distribution.

Assumption: the card can be served from `custom_components/cycle_tracker/www/`
and registered as a Lovelace resource by the integration on the supported Home
Assistant baseline. No user feedback or usage figures are available.

## Follow-up

- [ ] Implement the card and its static-path/Lovelace-resource registration in
      the roadmap Phase 1 change.
- [ ] Revisit this record if the card needs a release cadence independent of the
      integration.
