---
id: ADR-0013
title: Agent skills are pinned, indexed and reviewed
status: accepted
date: 2026-11-16
deciders: []
supersedes: null
superseded-by: null
related: []
---

# ADR-0013: Agent skills are pinned, indexed and reviewed

## Context

The project uses agent skills from the skills.sh ecosystem
(<https://www.skills.sh/>). `skills-lock.json` currently pins 14 skills by
source repository, path and content hash, drawn from `obra/superpowers`,
`vercel-labs`, `anthropics/skills`, `currents-dev` and `sleekdotdesign`.

What is missing is a record of why each skill is installed, where it is applied
and whether it still earns its place. Without that, installed skills accumulate:
nobody can tell an actively used skill from one that was tried once, updates are
invisible, and reviewing the setup means reading 14 `SKILL.md` files. Skills
also change agent behavior, so an unreviewed update is an unreviewed change to
the project's process.

## Decision

We will pin every agent skill per repository, list it in an index with its
purpose and lifecycle status, and gate promotion and retirement on observed
effect.

- **Source and pinning.** Skills come from the skills.sh ecosystem and are
  installed per repository, pinned in `skills-lock.json` by source repository,
  skill path and content hash.
- **Index.** Every installed skill is listed in `docs/skills/README.md` with:
  skill id, source repository and install URL, why the project uses it (which
  problem it solves), where it is applied, status (`trial`, `in use`,
  `retired`) and the date of the last review.
- **Lifecycle.** A skill enters as `trial`. It is promoted to `in use` only
  after it demonstrably changed the output of a real task. It is retired — and
  removed from `skills-lock.json` — when it does not.
- **Selection rule.** Prefer skills from the upstream project that owns the
  technology (for example `home-assistant/core` for Home Assistant,
  `trailofbits/skills` for test technique) over generic collections. Prefer
  skills that constrain the work (checklists, gates) over skills that add prose.
- **Review surface.** The index is what a human reviews, not the individual
  `SKILL.md` files. Re-pinning a skill is a review of that row.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Install skills globally per machine | The setup then differs per developer and per agent, and the project cannot state what process it follows. |
| Track skills in `skills-lock.json` only | The lock answers "what is installed and at which content hash", not "why, where, and does it still work". |
| Pin a branch or tag instead of a content hash | Upstream can move under the project silently. A hash makes every change to the skill a visible diff. |
| Keep the index in prose documentation or a changelog | It would describe the past, not the current set and its review dates. |
| Adopt a large generic skill collection wholesale | Volume is not value; generic skills are less likely to match Home Assistant conventions and add instruction load to every task. |

## Consequences

**Positive**

- The installed skill set is reproducible across machines and agents.
- A human reviews one index instead of 14 skill files, and can see which skills
  are on trial, in use or retired.
- Skills that never changed an outcome leave the repository instead of lingering.
- Upstream-first selection reduces drift from Home Assistant conventions and the
  prompt-injection surface of arbitrary collections.

**Negative / costs**

- The index and the lock must be updated together; two files can disagree.
- Every upstream update requires a deliberate re-pin and re-review rather than
  receiving improvements automatically.
- Judging a skill requires running it on a real task, so promotion is slower
  than installation.
- Retiring a skill can regress a workflow that depended on it implicitly.

**Risks and mitigations**

- The index rots if review dates are not honoured. Mitigation: make the last
  review date a required column and review the row whenever the skill is
  re-pinned or used on a change.
- A skill update can change behavior subtly. Mitigation: the content hash makes
  the update explicit and reviewable; never re-pin without reviewing the diff.
- An upstream repository can disappear or rewrite its history. Mitigation: the
  index records the source repository and install URL, and a skill that can no
  longer be fetched at its pinned hash is retired rather than trusted.
- A trial skill can linger indefinitely. Mitigation: `trial` is a temporary
  status; the review date shows how long it has been there.

## Follow-up

- [ ] Create `docs/skills/README.md` and triage the 14 skills currently in
      `skills-lock.json` into `trial`, `in use` or `retired`.
- [ ] Remove retired entries from `skills-lock.json` and the installed skill
      files.
- [ ] Add the re-pin and review step to the dependency-update procedure.
