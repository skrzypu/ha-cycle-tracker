---
id: BDR-0001
title: HACS custom repository distribution
status: accepted
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: []
---

# BDR-0001: HACS custom repository distribution

## Context

`README.md` states that the integration is not part of the HACS default
catalog and documents two installation paths: adding
`https://github.com/skrzypu/ha-cycle-tracker` as a HACS custom repository with
category Integration, and manually copying `custom_components/cycle_tracker/`
into the Home Assistant configuration directory.

`hacs.json` at the repository root declares the name `Cycle Tracker` and a
minimum Home Assistant version of `2026.1.0`. The `hacs-distribution`
specification defines packaging, manifest fields, the supported Home Assistant
version, versioned GitHub releases matching `manifest.json`, and explicitly
requires custom-repository-only distribution with no submission to the HACS
default catalog.

## Decision

We will distribute Cycle Tracker as a HACS custom repository, not through the
HACS default catalog, and keep manual installation as a fallback.

In scope: the HACS custom-repository installation path and the documented
manual copy of `custom_components/cycle_tracker/`. Out of scope: submission to
the HACS default catalog, and any Home Assistant add-on packaging.

## Alternatives considered

| Alternative | Why not |
|---|---|
| HACS default catalog | Not currently pursued; the specification forbids default-catalog submission, so the integration is not listed or searchable in HACS. |
| Manual installation only | No update path for users; every update requires copying files again. |
| Home Assistant add-on | Wrong packaging for an integration; an add-on does not deliver a custom component. |

## Expected impact

- **Users:** install by adding the repository URL as a HACS custom repository,
  or by copying the component manually. Users must know the repository URL
  because the integration is not discoverable in the HACS catalog.
- **Revenue / cost:** no direct revenue. Hosting cost is limited to the public
  GitHub repository and its releases.
- **Operations / support:** HACS provides the update path for HACS users;
  manual installations must be updated by hand. Release and versioning work is
  tied to GitHub releases matching `manifest.json`.
- **Risk / compliance:** no HACS catalog review or catalog discovery; the
  project carries its own packaging and release validation (HACS and hassfest
  checks in CI).

## Evidence

- `README.md` — installation section and the statement that the integration is
  not part of the HACS default catalog.
- `hacs.json` — name and minimum Home Assistant version `2026.1.0`.
- `openspec/specs/hacs-distribution/spec.md` — packaging, manifest,
  versioning, GitHub release, and custom-repository-only requirements.

Assumption: the project intends to keep the current single-maintainer,
GitHub-hosted distribution model. No user counts, download figures, or support
volumes are available.

## Follow-up

- [ ] Publish GitHub releases whose tag matches `version` in
      `custom_components/cycle_tracker/manifest.json`.
- [ ] Keep `hacs.json` at the repository root and do not open a default-catalog
      submission.
- [ ] Revisit this record if default-catalog listing or add-on packaging is
      proposed.
