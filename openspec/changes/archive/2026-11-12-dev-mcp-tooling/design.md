# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- The integration runs fully local (ADR-0001) and has no runtime network access.
  This change is development tooling only and must not alter that.
- Home Assistant ships a built-in Model Context Protocol server since 2025.2.
  The **Main URL** (`/api/mcp`) exposes all tools and requires an administrator
  account. The **Read-only** option applies only to the main URL; individual
  URLs under `/api/mcp/…` ignore it and are never read-only.
- The development machine has `opencode` 2.1.4 and Node 22. Docker is not
  installed (`docker: command not found`). There is no Linux OpenDesign release.
- `opencode mcp add` writes `mcp.servers.<name>` into the project
  `opencode.json`; that is the confirmed server map shape for 2.1.4.
  `opencode mcp list` reports only global servers and does not read project
  entries, so it cannot be used as evidence for this change.
- ADR-0002 records the HA MCP decision, ADR-0003 records the OpenDesign
  container decision.

## Goals / Non-Goals

**Goals:**

- Both MCP servers are configured in the repository and disabled by default.
- Enabling a server for a debugging session is a one-line edit, not a setup
  exercise.
- No credential is stored in the repository.
- The complete setup, including Docker installation, is documented so it can be
  repeated manually on another machine.

**Non-Goals:**

- Automating Docker installation or container lifecycle from the repository.
- Running OpenDesign through `start_run` or a nested agent.
- Exposing Home Assistant to the internet; the MCP URL is reached on the local
  network.
- Replacing the integration's runtime behavior or adding network calls to it.
- Adding CI checks that require a live Home Assistant or Docker.

## Decisions

**1. Bearer token, not OAuth.**
Use `oauth: false` with `Authorization: Bearer {file:~/.secrets/ha_mcp_token}`.
Rationale: Home Assistant OAuth requires the client URL to match the configured
internal or external URL and a browser flow, which is brittle on a laptop that
moves between networks. The `{file:…}` interpolation keeps the token out of the
config file and out of the repository. Alternative rejected: OAuth (browser
flow, URL coupling).

**2. Disabled by default, enabled per session.**
Both entries carry `disabled: true`. Rationale: enabling HA MCP sends entity
states, history, and logs to the model provider; read-only limits writes, not
exposure. Keeping the entry off means data leaves the instance only when the
developer deliberately turns it on. Alternative rejected: enabled by default
(accidental data exposure on every session).

**3. Home Assistant side: main URL only, Read-only ON, administrator token.**
The main URL is required because the development loop needs logs and history;
individual URLs ignore Read-only. The token is an administrator long-lived
access token stored at `~/.secrets/ha_mcp_token` with mode `600`. Rationale:
the main URL is the only endpoint where Read-only is enforced, and the admin
scope is unavoidable for it.

**4. OpenDesign as a Docker container, MCP over `docker exec`.**
Run `ghcr.io/nexu-io/od:latest` bound to `127.0.0.1:7456`, with the MCP server
reached through `docker exec -i open-design node /app/apps/daemon/dist/cli.js
mcp`. Rationale: there is no Linux release, the host Node is 22 while OpenDesign
expects 24, and `od` collides with GNU coreutils. The container is a preview and
design-system surface only; exported HTML/CSS in the repository stays canonical.
Alternative rejected: native source install (Node 24 plus pnpm) and `start_run`
with a nested agent (mounts, host networking, larger memory budget).

**5. Docker installation is a documented manual step.**
The repository documents the install and run commands but does not script them.
Rationale: Docker needs root privileges and a logout for group changes; a
script would hide that and fail halfway. The task list gives the exact commands
and the verification for each.

**6. Permissions: allow reads, deny mutations as defense in depth.**
Add rules that allow `homeassistant_*` and `opendesign_*`, and deny mutating
tools explicitly. Home Assistant Read-only is the real control; the permission
deny is a second layer in case the entry is ever enabled against an instance
without Read-only. Exact tool names are recorded after the first successful
connection, because Home Assistant exposes the tools of the configured LLM API
and names can change between versions.

**7. The HA host is recorded from the user's current network.**
The config uses `http://192.168.0.215:8123/api/mcp`. Rationale: the user
supplied the address — Home Assistant `2026.2.3` on the local network. The URL
stays in a single place so it is easy to update when the network changes.

**8. Repository stays the source of truth.**
OpenDesign container data is ephemeral and not a project store; final card
HTML/CSS is exported into the repository. The token lives outside the
repository and is referenced by path only.

## Risks / Trade-offs

- **Data exposure while enabled** → disabled by default; enable only for the
  debugging session; the token is not committed.
- **Administrator-scoped token leakage** → file outside the repository, mode
  `600`, rotate if exposed, and never paste it into a prompt or commit.
- **Home Assistant URL changes with the network** → single URL in one
  file; update the URL and restart the session.
- **Read-only misunderstood as privacy** → documented explicitly in the README
  and in ADR-0002.
- **Docker becomes a development dependency** → container is optional; the
  integration and its checks do not require it.
- **MCP config drift across opencode versions** → the shape is the one
  `opencode mcp add` writes; the task verifies the file parses in a standalone
  session and records the version used.
- **Tool-name drift** → permission rules use prefixes; exact names are recorded
  after the first connection and the deny list is tightened then.

## Migration Plan

1. Install Docker and start the OpenDesign container (manual, user-owned).
2. Create the Home Assistant long-lived token and enable MCP with Read-only.
3. Add the two entries and permissions to `opencode.json`; restart opencode.
4. Enable one entry at a time, record the exposed tool names, then disable it.
5. Rollback: set both entries back to `disabled: true` or delete them; nothing
   in the product depends on this tooling.

## Open Questions

- Whether to pin the OpenDesign image by digest instead of `latest`.
- Exact MCP tool names exposed by the configured Home Assistant LLM API.
