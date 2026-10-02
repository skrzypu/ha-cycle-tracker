## Project-Specific Test Engineer Rules for ha-cycle-tracker

### Test Strategy Overview

#### Python Tests (pytest)
```
tests/
├── unit/
│   ├── test_coordinator.py       # DataUpdateCoordinator logic, calculations
│   ├── test_sensors.py           # Sensor state computation
│   ├── test_calendar.py          # Calendar entity events
│   ├── test_config_flow.py       # Config flow steps
│   └── test_algorithms.py        # Prediction algorithms (WMA, std dev)
├── integration/
│   ├── test_ha_component.py      # Full HA component with test instance
│   └── test_services.py          # log_start, log_end services
├── contract/
│   └── test_ffi_contract.py      # Validate JSON against schema (future FFI)
├── e2e/
│   └── test_user_flows.py        # Simulate: log start → predict → log end
└── fixtures/
    ├── regular_cycles.json       # 28-day cycles
    ├── irregular_cycles.json     # 21-35 day variation
    ├── single_cycle.json         # Edge case: one entry
    └── anovulatory.json          # Edge case: no ovulation phase
```

### Contract Testing (Future FFI Ready)
- **Shared Schema**: `specs/ffi-contract.schema.json` (JSON Schema Draft 2020-12)
- **Python Side**: `jsonschema.validate()` on every FFI response (when FFI added)
- **CI Gate**: Test suite fails if schema validation fails
- **Versioning**: `ffi_version` field in all responses, bump on breaking changes

### Property-Based Testing (Python - hypothesis)
```python
# tests/unit/test_algorithms.py
from hypothesis import given, strategies as st
import statistics

@given(st.lists(st.integers(20, 40), min_size=2, max_size=20))
def test_std_dev_non_negative(cycles):
    """Standard deviation should always be non-negative."""
    if len(cycles) > 1:
        assert statistics.stdev(cycles) >= 0.0

@given(st.lists(st.floats(0.0, 1.0), min_size=3, max_size=10))
def test_wma_weights_normalize(weights):
    """WMA weights should normalize to sum = 1.0."""
    total = sum(weights)
    normalized = [w / total for w in weights]
    assert abs(sum(normalized) - 1.0) < 1e-10

@given(st.integers(1, 40))
def test_phase_transitions(day):
    """Phase transitions should be valid."""
    # Implementation depends on phase logic
    pass
```

### Pre-commit Hook Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, pyyaml]
        args: [--strict, --ignore-missing-imports]

  - repo: local
    hooks:
      - id: python-tests
        name: Python Tests
        entry: pytest tests/ -x --tb=short
        language: system
        pass_filenames: false
        always_run: true
        types: [python]

      - id: contract-validation
        name: FFI Contract Validation
        entry: python scripts/validate_contract.py
        language: system
        pass_filenames: false
        always_run: true
```

### CI Pipeline (GitHub Actions)
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  python-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-homeassistant-custom-component ruff mypy jsonschema pyyaml voluptuous hypothesis
      - name: Run pre-commit hooks
        run: pre-commit run --all-files
      - name: Python Tests
        run: pytest tests/ -x -v
      - name: Contract Validation
        run: python scripts/validate_contract.py
      - name: Lint & Typecheck
        run: ruff check . && mypy custom_components/ --strict

  hacs-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: HACS Validation
        uses: hacs/validation-action@main
```

### Verification Evidence (Required for Completion)
Per `verification-before-completion` skill, every task must show:
1. **Test Output**: `pytest tests/ -v` passing
2. **Contract Validation**: `python scripts/validate_contract.py` output showing schema compliance
3. **Lint/Typecheck**: `ruff check . && mypy --strict` passing
4. **Pre-commit**: `pre-commit run --all-files` passing

### Test Data Management
- Fixtures in `tests/fixtures/` (JSON) - shared by unit and contract tests
- Python reads via `json.load()` in pytest fixtures
- Single source of truth for reference cycles

### Debugging Protocol (from `systematic-debugging`)
1. **Observe**: Capture failing test output, JSON mismatch, calculation errors
2. **Hypothesize**: "Weight normalization off by one" / "Cycle day calculation off by one"
3. **Test**: Minimal reproduction - isolate function, check raw values
4. **Verify**: Fix passes all related tests, contract validation, no regressions