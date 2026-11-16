"""Framework-free domain layer for cycle tracking and prediction.

Nothing in this package may import Home Assistant, an HTTP client or a schema
library: ``tests/imports`` enforces that boundary with an AST walk so the
domain tests can run in plain Python (ADR-0005).
"""
