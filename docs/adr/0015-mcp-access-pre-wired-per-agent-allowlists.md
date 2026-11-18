---
id: ADR-0015
title: MCP access is pre-wired per agent; both servers stay disabled by default
status: accepted
date: 2026-11-17
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0002", "ADR-0007", "ADR-0008"]
---

# ADR-0015: MCP access is pre-wired per agent; both servers stay disabled by default

## Context

ADR-0002 (Home Assistant MCP) and ADR-0007 (OpenDesign MCP) both require
`disabled: true` by default, with the entry enabled manually for a debugging
session. That posture leaves the per-agent wiring unspecified: nothing in the
config states which agent may use which server once an entry is enabled.

Both servers were first enabled permanently in this session, with access scoped
per agent through `mcps` allowlists. The user reversed that before anything was
committed: neither server is needed for ordinary work on this project right now,
and permanent server startup plus tool-schema load was not worth paying for
occasional debugging or design sessions. The allowlists themselves proved
useful, because they separate "who may use a server" from "is the server
running".

The constraints that produced the old default remain: Home Assistant exposes
private household state, and the LAN address must not be committed to the
repository.

`oh-my-opencode-slim` provides a per-agent `mcps` field. Verified against the
plugin's dist: the field is an allowlist that supports `"*"` and `"!name"`, and
the plugin converts each agent's list into agent-level `<server>_*` allow/deny
permission rules. It is therefore a narrower mechanism than the global toggle:
exposure can be decided per agent once a server is enabled.

## Decision

We will keep both MCP servers `disabled: true` by default and pre-wire per-agent
access through the `mcps` allowlists in `.opencode/oh-my-opencode-slim.json`, so
enabling a debugging or design session is one boolean flip instead of a config
redesign.

Concretely:

- `opencode.json` keeps `disabled: true` on both the `homeassistant` and
  `opendesign` entries.
- `homeassistant` keeps the main URL `/api/mcp` with `oauth: false` and the
  administrator bearer token, and its host comes from the environment:
  `http://{env:HA_MCP_HOST}:8123/api/mcp`, so no LAN address is committed.
- `opendesign` keeps the explicit command
  `docker exec -i open-design node /app/apps/daemon/dist/cli.js mcp --daemon-url http://127.0.0.1:7456`.
- Both presets (`opencode-go-free`, `opencode-go-paid`) carry the same lists:
  `orchestrator` gets `["homeassistant", "opendesign"]`; `designer` gets the same
  pair with `opendesign` first; `oracle`, `explorer` and `fixer` get
  `["homeassistant"]`; `librarian` keeps its web/context servers and `observer`
  keeps `[]`.
- To use a server, set `"disabled": false` on that entry and restart opencode;
  the allowlists then decide which agents see its tools.
- Custom agents in `.opencode/agent/*.md` have no `mcps` field and are not
  covered by this mechanism; their effective tool set is the global rules plus
  their own permission block.
- The global denies stay in force: `homeassistant_*call_service*` and
  `opendesign_delete_*`. Server-side Read-only (ADR-0008) remains the primary
  write protection; the deny rules are a second layer. A live probe with the
  OpenDesign server enabled exposed 20 tools and neither `delete_file` nor
  `delete_project`, so that deny currently matches no tool.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep both servers always on | Tried first and rejected: neither server is needed for ordinary work now, and permanent startup plus tool-schema load is a cost without a matching need. |
| Drop the per-agent allowlists and rely on global permissions | Every agent would gain every tool the moment a server is enabled, regardless of what it needs. |
| Runtime switch, such as an env-var-driven `disabled` | opencode substitution is string-only and `disabled` is boolean, so no environment variable can toggle it. |
| Keep opt-in with no allowlists (ADR-0002/0007 as they were) | Enabling a server would still require deciding agent scope, which is the redesign this record removes. |
| Hardcode the LAN address in `opencode.json` | Commits private infrastructure detail to the repository. |
| Add an `mcps` field to the custom agent files | The plugin does not read a `mcps` field from custom agent frontmatter; the field would be silently ignored. |

## Consequences

**Positive**

- Enabling a server is one boolean flip plus a restart, and agent scope is
  already decided.
- While a server is disabled, no agent carries its tool schema or reaches its
  data.
- No private address or token enters the repository: hostname from the
  environment, token from `~/.secrets/ha_mcp_token`.

**Negative / costs**

- Enabling still needs a config edit and a restart; there is no switch at
  runtime.
- A stopped `open-design` container or an unset `HA_MCP_HOST` only surfaces at
  the moment of enabling, not before.
- The allowlists are duplicated in two presets and must be kept in sync.
- An enabled server's schema still adds context overhead to every agent that
  lists it.

**Risks and mitigations**

- Agent-level allowlists are enforced by the plugin, so a plugin change could
  alter them silently; re-verify the generated permission rules after upgrading
  `oh-my-opencode-slim`.
- Enabling Home Assistant sends entity states, history, and logs to the model
  provider; keep Read-only enabled on the main MCP URL and turn the entry off
  again when the debugging session ends.

## Follow-up

- [x] Add `mcps` allowlists to both presets in
      `.opencode/oh-my-opencode-slim.json`.
- [x] Keep `disabled: true` on both entries and route the HA host through
      `{env:HA_MCP_HOST}`.
- [x] Document the opt-in posture and `HA_MCP_HOST` in the README development
      section.
- [ ] Re-check that an enabled session exposes no `opendesign_delete_*` tools
      after an OpenDesign image upgrade.
