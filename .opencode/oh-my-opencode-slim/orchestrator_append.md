## ha-cycle-tracker — routing and gates

Pure-Python Home Assistant integration. Domain in `custom_components/cycle_tracker/domain/`,
adapters in the sibling modules.

Delegate by role:
- implementation (config flow, sensors, calendar, services, algorithms) → @fixer
- tests (pytest, contracts, E2E, pre-commit) → @test-engineer
- research (HA API, component patterns, HACS) → @librarian
- codebase navigation / search → @explorer
- UI/UX (config flow, Lovelace card) → @designer
- architecture, risk, debugging, review → @oracle
- delegation meta-coaching → @orchestrator-coach
- "is the agent/config documentation still true?" → @agent-auditor

Gates: `pre-commit run --all-files` must pass (ruff, ruff-format, mypy, pytest).
Never commit or push without explicit user permission.
Keep subagent replies concise: paths, line references and diffs — not full-file pastes.
