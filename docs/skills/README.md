# Agent skills used in this project

The index required by [ADR-0013](../adr/0013-agent-skills-pinned-indexed-reviewed.md):
every installed agent skill, why it is here, where it is applied, and whether it
still earns its place. A reviewer reads this file, not sixteen `SKILL.md` files.

Skills are installed per repository with the [skills.sh](https://www.skills.sh/)
CLI and pinned in [`skills-lock.json`](../../skills-lock.json) by source
repository, file path and content hash. The installed copies live in
`.agents/skills/` and are linked into the agent directories.

## Installed skills

Status: `in use` — the skill has demonstrably changed work in this repository;
`trial` — installed and applicable, not yet exercised. Removed skills are
listed under "Removed" with the reason.

### Test and verification

| Skill | Source | Why it is here | Applied where | Status |
| --- | --- | --- | --- | --- |
| [test-driven-development](https://skills.sh/obra/superpowers/test-driven-development) | `obra/superpowers` | Failing test first, then the implementation — the rule that kept the domain extraction honest | Every task in `openspec/changes/archive/2026-11-16-add-cycle-prediction` | in use |
| [verification-before-completion](https://skills.sh/obra/superpowers/verification-before-completion) | `obra/superpowers` | Evidence before a claim: run the command, quote the output | `pre-commit run --all-files`, `pytest`, `openspec validate` gates | in use |
| [requesting-code-review](https://skills.sh/obra/superpowers/requesting-code-review) | `obra/superpowers` | Self-review checklist before calling work done | Adapter and service changes, ADR-0005/0006 work | in use |
| [systematic-debugging](https://skills.sh/obra/superpowers/systematic-debugging) | `obra/superpowers` | Hypothesis → test → verify, instead of patching symptoms | Options-flow crash, entity-resolution failures | in use |
| [test-quality-inspector](https://skills.sh/bobmatnyc/claude-mpm-skills/test-quality-inspector) | `bobmatnyc/claude-mpm-skills` | Assertion-quality and red-flag checklist; the human answer to "is this test actually testing anything" | ADR-0012 review gate, E2E audit in `tests/e2e` | trial |
| [ha-integration-knowledge](https://skills.sh/home-assistant/core/ha-integration-knowledge) | `home-assistant/core` (official) | How Home Assistant expects integrations, entities, config flows and tests to be built | Entity platforms, config flow, service registration | trial |
| [deslop](https://skills.sh/cristiano-pacheco/ai-tools/deslop) | `cristiano-pacheco/ai-tools` | Removes AI-generated code slop from a branch diff before commit/PR | `fixer` pre-commit pass | trial |
| [caveman-review](https://skills.sh/juliusbrussee/caveman/caveman-review) | `juliusbrussee/caveman` | Compressed review: one line per finding with location, problem, fix | `oracle` review output | trial |

### Workflow and planning

| Skill | Source | Why it is here | Applied where | Status |
| --- | --- | --- | --- | --- |
| [writing-plans](https://skills.sh/obra/superpowers/writing-plans) | `obra/superpowers` | Multi-step work gets a plan with checkpoints | OpenSpec change planning | in use |
| [executing-plans](https://skills.sh/obra/superpowers/executing-plans) | `obra/superpowers` | Running a plan in-session, step by step, with verification | Task-by-task implementation | in use |
| [dispatching-parallel-agents](https://skills.sh/obra/superpowers/dispatching-parallel-agents) | `obra/superpowers` | Splitting independent lanes instead of serialising them | Adapter lanes, docs lane beside code lane | in use |
| [subagent-driven-development](https://skills.sh/obra/superpowers/subagent-driven-development) | `obra/superpowers` | Specialists own their scope; the orchestrator reconciles | Every delegated lane | in use |
| [finishing-a-development-branch](https://skills.sh/obra/superpowers/finishing-a-development-branch) | `obra/superpowers` | Tests, commit message, PR text, review request as one close-out | Branch close-out | trial |
| [find-skills](https://skills.sh/vercel-labs/skills/find-skills) | `vercel-labs/skills` | Discovery across skills.sh; found the two skills above | This index | in use |
| [concise-planning](https://skills.sh/sickn33/agentic-awesome-skills/concise-planning) | `sickn33/agentic-awesome-skills` | Clear, atomic checklists for coding tasks | `orchestrator` planning | trial |

### Output economy

| Skill | Source | Why it is here | Applied where | Status |
| --- | --- | --- | --- | --- |
| [caveman](https://skills.sh/juliusbrussee/caveman/caveman) | `juliusbrussee/caveman` | Terse output — answers first, fluff gone, technical facts kept | `fixer`, `oracle`, `explorer` replies | trial |

### Removed 2026-11-16

| Skill | Source | Why it left |
| --- | --- | --- |
| agent-browser | `vercel-labs/agent-browser` | No browser surface; Lovelace card parked |
| playwright-best-practices | `currents-dev/playwright-best-practices-skill` | Tests are pytest, not Playwright |
| webapp-testing | `anthropics/skills` | Same |
| sleek-design-mobile-apps | `sleekdotdesign/agent-skills` | Mobile app design, not a HA integration |
| caveman-compress | `juliusbrussee/caveman` | Ships executable `scripts/`; declined on risk for now |

Re-adding any of these is `npx skills add <source>@<skill>` plus a row back in
the tables above.

## Considered and rejected

| Skill | Source | Why not |
| --- | --- | --- |
| mutation-testing | `trailofbits/skills` | Its workflows drive `mewt`/`muton`, a Go mutation-testing toolchain. [ADR-0012](../adr/0012-e2e-tests-verify-shipped-contract.md) prescribes a manual, targeted mutation check per changed E2E test instead. |
| e2e-testing-patterns | `wshobson/agents` | Playwright/Cypress, browser journeys and selectors. The E2E suite here is pytest through `hass`; the portable parts (critical journeys only, no internals) are already in ADR-0012. |
| test-quality-analysis | `secondsky/claude-skills` | Generic TypeScript-flavoured smell list; overlaps `test-quality-inspector`, which brings an explicit checklist and red flags. |
| fixing-flaky-tests | `posthog/posthog` | Nothing in the suite is flaky today; the determinism rule in ADR-0012 is the cheaper guard. |
| property-based-testing | `trailofbits/skills` | Genuine fit for the pure domain (strategies, windows, rounding invariants) but needs a `hypothesis` dependency. Deferred, not rejected — revisit if the algorithm tests need broader input coverage than the example table gives. |

## Reviewing this index

A skill is reviewed when it is installed and then on a first-use basis. Ask, in
order:

1. Did the skill change an output of a real task? If not after it was
   applicable, it is `trial` at best — or it should go.
2. Does its guidance conflict with an ADR, an OpenSpec spec or the Home
   Assistant conventions? The repository rules win; a conflicting skill is
   retired.
3. Is it still pinned, and does `npx skills update` change its hash? An update
   is a new review, not a silent refresh: read the diff before accepting it.

Only `in use` skills may be cited as a reason a change was made a certain way.

## Keeping the index honest

A read-only native agent, `@agent-auditor` (`.opencode/agent/agent-auditor.md`),
cross-checks this index, the agent prompts, `docs/adr/`, `docs/guide/` and
`README.md` against the actual code, and reports stale, duplicated, fabricated
or contradictory claims as a `file:line → verdict → evidence` table. Run it on
request ("audit agents") or before any change to the agent system.

> Install note: `concise-planning` was requested from `jpropato/siba`, which
> fails Git auth; the most-installed registry source
> `sickn33/agentic-awesome-skills@concise-planning` was installed instead.
