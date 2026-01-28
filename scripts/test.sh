#!/usr/bin/env bash
set -euo pipefail

# Load .env then .env.test (test overrides)
set -a
[ -f .env ] && source .env
[ -f .env.test ] && source .env.test
set +a

# Run pytest, explicitly targeting the tests directory
# pytest auto-discovers test_*.py files, so this will find:
# - tests/test_integration_core_flow.py (all 4 integration tests)
pytest -q tests/
