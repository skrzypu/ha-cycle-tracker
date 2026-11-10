---
id: ADR-0002
title: Home Assistant MCP is read-only development tooling, disabled by default
status: accepted
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0001"]
---

# ADR-0002: Home Assistant MCP is read-only development tooling, disabled by default

## Context

The development loop needs to inspect entity states, attributes, history, and
logs on a running Home Assistant instance. Home Assistant ships a built-in Model
Context Protocol (MCP) server since 2025.2.

The main MCP URL exposes all tools and requires an administrator account. The
Read-only option applies only to the main URL; individual URLs ignore it. This
tooling is separate from the integration's runtime, which remains local-only
under ADR-0001.

## Decision

We will use the Home Assistant MCP server as read-only development tooling,
disabled by default.

Concretely:

- opencode connects to the main MCP URL `/api/mcp` with `oauth: false` and
  `Authorization: Bearer {file:~/.secrets/ha_mcp_token}`.
- The opencode MCP entry is `disabled: true` by default and must be enabled
  manually for debugging.
- The Home Assistant Model Context Protocol integration has Read-only enabled.
- The token is an administrator long-lived access token stored outside the
  repository.

## Alternatives considered

| Alternative | Why not |
|---|---|
| OAuth | Requires the MCP URL to match the Home Assistant internal/external URL and a browser flow. |
| `/api/mcp/assist` | Exposes only the entities exposed to Assist and provides no logs. |
| No MCP (status quo) | The development loop lacks direct access to states, attributes, history, and logs. |

## Consequences

**Positive**

- Direct access to entity states, attributes, history, and logs during
  development.
- Read-only mode prevents tool-driven writes to the Home Assistant instance.

**Negative / costs**

- Read-only limits writes, not data exposure: cycle data, entity states,
  history, and logs are sent to the model provider.
- The token is administrator-scoped, so its leakage would grant administrative
  access.
- The MCP entry must be enabled manually before each debugging session.
- Tools are exposed to the model as `homeassistant_*`, which adds tool-selection
  overhead.

**Risks and mitigations**

- Sensitive cycle data leaves the instance when MCP is enabled; keep the entry
  disabled by default and enable it only for debugging.
- Administrator token exposure; keep the token in `~/.secrets/` outside the
  repository and rotate it if compromised.

## Follow-up

- [ ] Create the long-lived administrator token and store it at
      `~/.secrets/ha_mcp_token`.
- [ ] Revisit this record if Home Assistant changes the MCP URL, Read-only
      behavior, or authentication model.
