---
id: ADR-0003
title: OpenDesign runs as a Docker workshop, not a nested agent
status: accepted
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: []
---

# ADR-0003: OpenDesign runs as a Docker workshop, not a nested agent

## Context

OpenDesign is used as a preview and design-system surface for the Lovelace card
work. There is no Linux release, and the development machine has Node 22 but
neither Node 24 nor pnpm. The `od` binary name collides with GNU coreutils.
Docker can be installed.

OpenDesign data lives in a Docker volume and is not a project store, so the
repository cannot rely on it as the source of truth.

## Decision

We will run OpenDesign as the Docker container `ghcr.io/nexu-io/od:latest`
bound to `127.0.0.1:7456`, and access its MCP server through
`docker exec -i open-design node /app/apps/daemon/dist/cli.js mcp`.

We use it as a preview and design-system surface only. We do not use
`start_run` or a nested agent initially. The final HTML/CSS is exported to the
repository, which remains the source of truth.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Native source install | Requires Node 24 and pnpm, neither of which is installed; no Linux release is available. |
| OpenDesign on a LAN machine | Moves the tool off the development machine and adds network and access management. |
| No daemon, only `DESIGN.md` and a vendored skill | Loses the live preview and design-system surface. |
| `start_run` with a nested agent | Requires `Dockerfile.local`, mounts, host networking, and a larger memory budget. |

## Consequences

**Positive**

- Works with the installed toolchain; Docker is the only new dependency.
- OpenDesign's MCP server is reachable from the host through `docker exec`.

**Negative / costs**

- Docker becomes a development dependency.
- Container data is ephemeral and must be exported to the repository.
- The MCP server is available only while the container runs.
- The container is a preview surface, not the source of truth.

**Risks and mitigations**

- Losing container state; export final HTML/CSS to the repository and treat the
  repository as canonical.
- Tooling drift from `od:latest`; pin the image tag if reproducibility becomes
  necessary.

## Follow-up

- [ ] Install Docker and start the `open-design` container on `127.0.0.1:7456`.
- [ ] Export the final card HTML/CSS into the repository.
