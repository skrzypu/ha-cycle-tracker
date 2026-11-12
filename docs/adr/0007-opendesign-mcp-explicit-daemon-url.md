---
id: ADR-0007
title: OpenDesign MCP requires an explicit daemon URL
status: accepted
date: 2026-11-12
deciders: []
supersedes: "ADR-0003"
superseded-by: null
related: ["ADR-0002"]
---

# ADR-0007: OpenDesign MCP requires an explicit daemon URL

## Context

ADR-0003 established OpenDesign as a Docker workshop: the container
`ghcr.io/nexu-io/od:latest` binds `127.0.0.1:7456`, and its MCP server is a
stdio process started inside the container. opencode reaches that process with
`docker exec -i open-design node /app/apps/daemon/dist/cli.js mcp`.

During implementation of `dev-mcp-tooling`, the MCP process did not find its
daemon when started this way. OpenDesign's auto-discovery (sidecar status and
registration) does not work across `docker exec`, so the daemon address must be
supplied on the command line. This makes ADR-0003's recorded command incomplete;
the Docker-workshop and no-nested-agent decisions in that record still stand.

Two related facts were verified during the same change: the container's runtime
data directory is `/app/.od`, the mount point of the named volume
`open-design-data`; and `ghcr.io/nexu-io/od:latest` pulls anonymously, so no
registry credentials are needed.

## Decision

We will keep OpenDesign as a Docker workshop and reach its MCP server through
`docker exec -i open-design node /app/apps/daemon/dist/cli.js mcp --daemon-url
http://127.0.0.1:7456`, always passing the daemon URL explicitly.

Concretely:

- The container runs from `ghcr.io/nexu-io/od:latest`, bound to
  `127.0.0.1:7456`.
- Runtime data lives in the named volume `open-design-data`, mounted at
  `/app/.od`.
- The `opendesign` MCP entry in `opencode.json` includes `--daemon-url
  http://127.0.0.1:7456` in its command and stays `disabled: true` by default.
- OpenDesign remains a preview and design-system surface; exported HTML/CSS in
  the repository is canonical.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Rely on daemon auto-discovery (ADR-0003's command) | Sidecar status and registration are not visible to a process spawned by `docker exec`; the MCP server cannot locate the daemon. |
| Start the MCP server through the container network namespace or host networking | Adds container/runtime changes for a problem the explicit URL solves with one flag. |
| Bind-mount data to a host directory instead of a named volume | The volume is already documented and working; a host path adds permission and backup concerns. |
| Native source install | Requires Node 24 and pnpm, neither installed; no Linux release (unchanged from ADR-0003). |

## Consequences

**Positive**

- The MCP server starts reliably regardless of how the container is spawned.
- The daemon address is explicit in the config, so the transport does not
  depend on undocumented discovery behavior.
- The image needs no registry authentication, and the data directory is known.

**Negative / costs**

- The daemon URL duplicates the published port; changing the port requires
  updating both the `docker run` command and the MCP command.
- `/app/.od` and the volume layout are OpenDesign implementation details that
  may change between image versions.
- The MCP server is available only while the container runs.

**Risks and mitigations**

- Image drift from `:latest` changes the data path or CLI; pin a digest if
  reproducibility becomes necessary, and re-verify the command after upgrades.
- A future OpenDesign version fixes auto-discovery or changes the flag;
  re-verify `--daemon-url` on upgrade.

## Follow-up

- [x] Implemented by `openspec/changes/dev-mcp-tooling`; `opencode.json` carries
      the corrected command.
- [ ] Re-verify `/app/.od` and `--daemon-url` when the OpenDesign image changes.
