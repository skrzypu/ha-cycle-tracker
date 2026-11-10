# Proposal

## Why

Development currently has no direct access to a running Home Assistant
instance and no design preview surface: entity states, history, and logs must be
copied by hand, and the card has no way to be previewed against real data. That
turns every debugging session into guesswork. The setup also exists only as
tribal knowledge, so it is not repeatable.

## What Changes

- Configure two opt-in MCP servers in `opencode.json`, both disabled by default:
  - `homeassistant` — remote MCP against the Home Assistant main URL
    `/api/mcp`, bearer-token auth read from `~/.secrets/ha_mcp_token`, no OAuth.
  - `opendesign` — local MCP that attaches to the OpenDesign Docker container
    over stdio.
- Add permission rules that allow read tools and deny mutating tools as defense
  in depth, even though Home Assistant Read-only is enforced server-side.
- Document the complete manual setup in `README.md`: Home Assistant MCP
  enablement and read-only mode, long-lived token creation and storage, Docker
  installation, the OpenDesign container run command, and how to enable each
  MCP entry for a debugging session.
- Record the Home Assistant host and version as a placeholder (`<HA_HOST>`)
  until the user provides the current network address.
- No product or runtime behavior changes: the integration keeps running fully
  local under ADR-0001.

## Capabilities

### New Capabilities

None. This change touches only developer tooling and documentation; it changes
no system behavior that a spec should pin. The change's `.openspec.yaml` sets
`skip_specs: true`.

### Modified Capabilities

None.

## Impact

- **Modified files**: `opencode.json` (MCP servers and permissions),
  `README.md` (development tooling section).
- **Unchanged**: everything under `custom_components/`, `openspec/specs/`,
  storage, services, entities, and CI.
- **Manual prerequisites owned by the user**: Home Assistant MCP enabled with
  Read-only, an administrator long-lived token stored outside the repository,
  Docker installed, and the OpenDesign container running.
- **Secrets**: no credential is committed; the config references a file path
  outside the repository.
