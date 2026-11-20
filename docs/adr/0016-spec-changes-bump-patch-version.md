---
id: ADR-0016
title: Each archived OpenSpec change bumps the patch version
status: accepted
date: 2026-11-20
deciders: []
supersedes: null
superseded-by: null
related: []
---

# ADR-0016: Each archived OpenSpec change bumps the patch version

## Context

The integration's version lives in one place: `"version"` in
`custom_components/cycle_tracker/manifest.json` (currently `0.2.6`). Two
consumers depend on it. HACS detects a new release from that value, so a change
that ships without a bump is invisible to users who installed through HACS. The
bundled Lovelace card is served as a static path with caching enabled, and its
resource URL carries a `?v=` cache-buster that `__init__.py` derives from the
manifest version at runtime (`_card_resource_url`). The example card URL in the
main `README.md` carries the same `?v=` value.

Nothing currently states when the version changes. Without a rule, a spec change
can be archived and released with the version left untouched: HACS reports no
update, and browsers keep serving the cached card because the `?v=` is
unchanged. The failure is silent — the code changed, but users see neither an
update prompt nor the new card.

## Decision

We will bump the patch (smallest) version in the manifest for every OpenSpec
change that reaches the archive, unless we consciously decide in that change to
use a minor or major bump instead.

- The version in `custom_components/cycle_tracker/manifest.json` is the single
  source of truth. The current agreed value is `0.2.6`.
- The default bump is patch (`0.2.5` -> `0.2.6`). A minor or major bump is made
  only by an explicit decision in that change, never by default.
- The `v=` in the example card URL in the main `README.md` must be kept in sync
  with the manifest version.
- The card cache-buster is not maintained by hand: `__init__.py` reads the
  manifest version and builds the `?v=` query string dynamically, so the
  resource URL changes whenever the manifest does.
- Bumping the version is a repository change and part of the OpenSpec change
  itself — it is committed with the change, not produced as a side effect of
  building or packaging a release.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Bump patch only for "small" changes and choose ad hoc otherwise | Leaves the HACS/card failure to intuition; there is no objective trigger for when to bump. |
| Bump minor for every change | Overstates routine changes and exhausts the minor range quickly. |
| Let the build or packaging step inject the version | The bump would not be a reviewed part of the change, and the manifest would stop being the stable source of truth. |
| Maintain the `?v=` cache-buster by hand in the resource config | It drifts from the manifest; a missed edit reproduces the cached-card bug. |

## Consequences

**Positive**

- Every archived change is installable and visible to HACS users.
- The card URL changes with every bump, so browsers fetch the new asset.
- One authoritative version: the README example and the runtime cache-buster
  both follow it.

**Negative / costs**

- Every change carries a one-line manifest edit (plus a README `v=` edit), so
  version churn is higher.
- Contributors must remember the bump as part of archiving; a missed bump is
  easy to make unless it is checked.

**Risks and mitigations**

- A change archived without a bump ships silently (no HACS update, stale card).
  Mitigate by checking the manifest version and README `v=` during archive
  review.
- The README `v=` is manual and can lag; keep it alongside the manifest edit in
  the same change.

## Follow-up

- [ ] Verify `0.2.6` is set in the manifest and in the README example card URL.
- [ ] Add an archive-time check that the manifest version and README `v=` were
      bumped as part of the change.
