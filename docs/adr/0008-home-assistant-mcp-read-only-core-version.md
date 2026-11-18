---
id: ADR-0008
title: Home Assistant MCP Read-only requires Core 2026.10+
status: accepted
date: 2026-11-12
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0002", "ADR-0007", "ADR-0015"]
---

# ADR-0008: Home Assistant MCP Read-only requires Core 2026.10+

## Context

ADR-0002 requires the Home Assistant MCP integration to run with Read-only
enabled on the main URL `/api/mcp`. That record did not state a Core version
requirement.

The Read-only option and the integration's **Configure** options flow were added
in Home Assistant Core 2026.10. The development instance initially ran 2026.2.3,
where the option was absent; updating to 2026.11.1 made it available. The
requirement is therefore a hard prerequisite, not a preference.

With Read-only enabled on 2026.11.1, `/api/mcp` exposed 12 tools, none of which
write or call services: `homeassistant__GetLiveContext`, `llm__GetDateTime`,
`todo__get_items`, `config__get_config_entries`,
`config__search_integrations`, `hassio__get_logs`, `history__get_history`,
`homeassistant__render_template`, `homeassistant__search_actions`,
`search__search`, `system_health__get_system_info`, and
`system_log__get_entries`. The exposed set depends on the configured LLM API and
installed integrations, so it is evidence that Read-only held, not a stable
contract.

## Decision

We will require Home Assistant Core 2026.10 or newer for the MCP development
tooling, and enable Read-only on the main MCP URL before using it.

Concretely:

- The development instance must run Core 2026.10+; on older versions the
  Read-only option does not exist and the MCP entry stays disabled.
- Read-only is enabled through **Settings → Devices & services → Model Context
  Protocol → Configure**.
- The transport from ADR-0002 is unchanged: main URL `/api/mcp`,
  `oauth: false`, administrator bearer token from `~/.secrets/ha_mcp_token`,
  `disabled: true` by default.
- The permission deny rule for `homeassistant_*call_service*` remains a second
  layer; it is not a substitute for server-side Read-only.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Stay on Core 2026.2.3 without Read-only | No server-side write protection; an administrator token could call services. The permission deny alone is a single client-side layer. |
| Use an individual MCP URL | Individual URLs ignore Read-only and are never read-only. |
| Upgrade opportunistically without recording a minimum | Future readers would repeat the same dead end on an old Core. |
| OAuth | Already rejected in ADR-0002: URL coupling and a browser flow. |

## Consequences

**Positive**

- Read-only is enforced by Home Assistant, not only by opencode permissions.
- The version prerequisite is explicit, so setup does not stall on a missing
  options flow.
- The observed tool set confirms the read-only posture on 2026.11.1.

**Negative / costs**

- The development instance must track a recent Core release; older test
  instances cannot use this tooling.
- Read-only limits writes, not exposure: entity states, history, and logs still
  reach the model provider when the entry is enabled.
- The 12-tool list drifts with Core and installed integrations, so it is not a
  stable allowlist.

**Risks and mitigations**

- An instance without Read-only is used by mistake; keep the entry disabled by
  default, verify the tool list, and rely on the deny rule as a fallback.
- Tool names change between versions; keep permission rules prefix-based and
  re-record names after upgrades.

## Follow-up

- [x] Upgraded the development instance from Core 2026.2.3 to 2026.11.1 and
      enabled Read-only.
- [x] Recorded the 12 observed read-only tools during `dev-mcp-tooling`.
- [ ] Link this record from the README development section when that section is
      next revised.
