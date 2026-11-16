# Architecture Decision Records

Durable technical decisions for this project.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-local-only-storage.md) | Local-only data storage and processing | accepted | 2026-11-09 |
| [0002](0002-read-only-ha-mcp-development-tooling.md) | Home Assistant MCP is read-only development tooling, disabled by default | accepted | 2026-11-09 |
| [0003](0003-opendesign-docker-workshop.md) | OpenDesign runs as a Docker workshop, not a nested agent | superseded | 2026-11-09 |
| [0004](0004-google-sheets-source-of-truth.md) | Google Sheets is the source of truth for cycle data | proposed | 2026-11-09 |
| [0005](0005-solid-and-clean-architecture.md) | SOLID and Clean Architecture as design constraints | accepted | 2026-11-09 |
| [0006](0006-domain-model-contract.md) | Explicit, framework-free domain model contract | accepted | 2026-11-10 |
| [0007](0007-opendesign-mcp-explicit-daemon-url.md) | OpenDesign MCP requires an explicit daemon URL | accepted | 2026-11-12 |
| [0008](0008-home-assistant-mcp-read-only-core-version.md) | Home Assistant MCP Read-only requires Core 2026.10+ | accepted | 2026-11-12 |
| [0009](0009-documentation-mermaid-portable-markdown.md) | Documentation uses Mermaid diagrams in portable Markdown | accepted | 2026-11-12 |
| [0010](0010-service-call-config-entry-resolution.md) | Service calls resolve their config entry from the call target | accepted | 2026-11-15 |
| [0011](0011-config-entry-owns-settings.md) | The config entry owns settings; integration storage owns periods | accepted | 2026-11-15 |
| [0012](0012-e2e-tests-verify-shipped-contract.md) | E2E tests verify the shipped contract, and their strength is proven by mutation | accepted | 2026-11-16 |
| [0013](0013-agent-skills-pinned-indexed-reviewed.md) | Agent skills are pinned, indexed and reviewed | accepted | 2026-11-16 |
| [0014](0014-agent-auditor-verifies-config-truth.md) | An agent auditor periodically verifies that agent and config documentation is still true | accepted | 2026-11-16 |
