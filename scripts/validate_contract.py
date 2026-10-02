#!/usr/bin/env python3
"""FFI Contract Validation Script

Validates both KMP FFI output and Python FFI input against the shared JSON schema.
"""

import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    print("jsonschema not installed. Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load JSON schema from file."""
    with open(schema_path, "r") as f:
        return json.load(f)


def validate_json(data: dict[str, Any], schema: dict[str, Any], name: str) -> bool:
    """Validate JSON data against schema."""
    try:
        jsonschema.validate(instance=data, schema=schema)
        print(f"✓ {name} validation passed")
        return True
    except jsonschema.ValidationError as e:
        print(f"✗ {name} validation failed: {e.message}")
        print(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        return False
    except jsonschema.SchemaError as e:
        print(f"✗ {name} schema error: {e.message}")
        return False


def main() -> int:
    """Main validation entry point."""
    schema_path = Path("specs/ffi-contract.schema.json")
    
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}")
        print("Run this script from the project root directory.")
        return 1
    
    schema = load_schema(schema_path)
    
    # Test data for validation
    test_cases = [
        # FFI Create Config
        ({
            "initialPeriods": [
                {"startDate": {"year": 2024, "month": 1, "day": 1}, "endDate": {"year": 2024, "month": 1, "day": 5}, "flowIntensity": "MEDIUM"},
                {"startDate": {"year": 2024, "month": 1, "day": 29}, "endDate": {"year": 2024, "month": 2, "day": 2}, "flowIntensity": "LIGHT"}
            ],
            "averageCycleLength": 28,
            "averagePeriodLength": 5
        }, "FfiCreateConfig"),
        
        # FFI Period Entry
        ({
            "startDate": {"year": 2024, "month": 1, "day": 1},
            "endDate": {"year": 2024, "month": 1, "day": 5},
            "flowIntensity": "MEDIUM",
            "notes": "Test period"
        }, "FfiPeriodEntry"),
        
        # FFI LocalDate
        ({
            "year": 2024,
            "month": 1,
            "day": 15
        }, "FfiLocalDate"),
        
        # FFI Prediction Result
        ({
            "nextPeriodStart": {"year": 2024, "month": 2, "day": 12},
            "cyclePhase": {"name": "FOLLICULAR"},
            "daysUntilNextPeriod": 14,
            "confidence": 0.75
        }, "FfiPredictionResult"),
        
        # FFI Cycle Phase
        ({
            "name": "OVULATION"
        }, "FfiCyclePhase"),
        
        # FFI Statistics
        ({
            "averageCycleLength": 28.5,
            "averagePeriodLength": 5.2,
            "cycleLengthStdDev": 2.1,
            "periodLengthStdDev": 1.3,
            "totalCyclesTracked": 6,
            "shortestCycle": 25,
            "longestCycle": 32
        }, "FfiStatistics"),
    ]
    
    all_passed = True
    for test_data, name in test_cases:
        if not validate_json(test_data, schema, name):
            all_passed = False
    
    if all_passed:
        print("\n✓ All contract validations passed")
        return 0
    else:
        print("\n✗ Some contract validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())